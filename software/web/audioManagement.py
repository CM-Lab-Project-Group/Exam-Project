import math
import array
from collections import deque
import threading
import wave
import sounddevice as sd

class AudioReader:
    CHUNK_SIZE = 1024
    CHANNELS = 2
    RATE = 44100
    DTYPE = "int16"
    FRAMES_TO_KEEP = 50
    MAX_INT16 = 32_768.0

    def __init__(self, device: int | str | None = None) -> None:
        self._frames: deque[bytes] = deque(maxlen=self.FRAMES_TO_KEEP)
        self._lock = threading.Lock()
        self._stream = sd.RawInputStream(
            samplerate=self.RATE,
            blocksize=self.CHUNK_SIZE,
            device=device,
            channels=self.CHANNELS,
            dtype=self.DTYPE,
            callback=self._audio_callback
        )

    def _audio_callback(self, indata, frames: int, time_info, status: sd.CallbackFlags) -> None:
        chunk = bytes(indata)
        with self._lock:
            self._frames.append(chunk)

    @property
    def volume(self) -> float:
        """Return current input volmue (Root Mean Square) normalized between 0.0 and 1.0 (both inclusive)"""
        with self._lock:
            if not self._frames:
                return 0.0
            latest_frame = self._frames[-1]

        samples = array.array("h")
        samples.frombytes(latest_frame)
        if not samples:
            return 0.0

        root_mean_square = math.sqrt(sum(s * s for s in samples) / len(samples))
        return min(root_mean_square / self.MAX_INT16, 1.0)

    def start_recording(self):
        if not self._stream.active:
            self._stream.start()

    def stop_recording(self) -> None:
        if self._stream.active:
            self._stream.stop()

    def get_frames(self) -> list[bytes]:
        with self._lock:
            return list(self._frames)

    def save_wav(self, filename: str) -> None:
        frames = self.get_frames()
        with wave.open(filename, "wb") as wav:
            self._dump_to_wav(frames, wav)

    def _dump_to_wav(self, frames: list[bytes], wav: wave.Wave_write):
        wav.setnchannels(self.CHANNELS)
        wav.setsampwidth(2)
        wav.setframerate(self.RATE)
        wav.writeframes(b"".join(frames))

    def close(self) -> None:
        self.stop_recording()
        self._stream.close()

if __name__ == "__main__":
    import time

    reader = AudioReader()
    reader.start_recording()

    for _ in range(20):
        print(f"Volume: {reader.volume:.3f}")
        time.sleep(0.1)

    reader.close()
