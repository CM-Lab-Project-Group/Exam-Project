import time
import math
import array
from collections import deque
import threading
from typing import Any
import wave
import sounddevice as sd
from videoStreaming import DATA_DIR

AUDIO_RECORDINGS_DIR = DATA_DIR / "audio"
AUDIO_RECORDINGS_DIR.mkdir(exist_ok=True)

def get_input_devices(default_hostapi_only: bool = True) -> list[dict]:
    """Return available microphone/input devices."""
    default_input_idx = sd.default.device[0]
    default_hostapi = sd.default.hostapi
    devices = []

    for idx, dev in enumerate(sd.query_devices()):
        if dev["max_input_channels"] <= 0:
            continue
        if default_hostapi_only and dev["hostapi"] != default_hostapi:
            continue

        devices.append({
            "index": idx,
            "name": dev["name"],
            "channels": dev["max_input_channels"],
            "default_samplerate": int(dev["default_samplerate"]),
            "is_default": idx == default_input_idx,
        })

    return devices

class AudioReader:
    CHUNK_SIZE = 1024
    CHANNELS = 2
    RATE = 44100
    DTYPE = "int16"
    MAX_INT16 = 32_768.0
    MIN_DBFS = -60.0

    def __init__(self, buffer_seconds: float = 5.0, device: int | str | None = None) -> None:
        self._buffer_seconds = buffer_seconds
        self._frames: deque[bytes] = deque(maxlen=self._seconds_to_chunks(buffer_seconds))
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
    def buffer_seconds(self) -> float:
        return self._buffer_seconds

    @buffer_seconds.setter
    def buffer_seconds(self, seconds: float) -> None:
        new_maxlen = self._seconds_to_chunks(seconds)
        with self._lock:
            self._buffer_seconds = seconds
            self._frames = deque(self._frames, maxlen=new_maxlen)

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

    @property
    def volume_dbfs(self) -> float:
        rms_norm = self.volume
        if rms_norm <= 0.0:
            return self.MIN_DBFS
        dbfs = 20.0 * math.log10(rms_norm)
        return max(dbfs, self.MIN_DBFS)

    @property
    def volume_percent(self) -> float:
        clamped = min(max(self.volume_dbfs, self.MIN_DBFS), 0.0)
        return ((clamped - self.MIN_DBFS) / abs(self.MIN_DBFS)) * 100.0

    @property
    def input_device(self) -> list[dict[str, Any]]:
        return sd.query_devices(self._stream.device)

    def start_recording(self):
        if not self._stream.active:
            self._stream.start()

    def stop_recording(self) -> None:
        if self._stream.active:
            self._stream.stop()

    def get_frames(self) -> list[bytes]:
        with self._lock:
            return list(self._frames)

    def _generate_filename(self):
        current_time = time.time()
        seconds_timestamp = int(current_time * 1000)
        return f"audio_{seconds_timestamp}.wav"

    def save_wav(self, filename: str | None = None) -> str:
        if filename is None:
            filename = self._generate_filename()
        file_path = AUDIO_RECORDINGS_DIR / filename
        frames = self.get_frames()
        with wave.open(file_path, "wb") as wav:
            self._dump_to_wav(frames, wav)
        return filename

    def _dump_to_wav(self, frames: list[bytes], wav: wave.Wave_write):
        wav.setnchannels(self.CHANNELS)
        wav.setsampwidth(2)
        wav.setframerate(self.RATE)
        wav.writeframes(b"".join(frames))

    def close(self) -> None:
        self.stop_recording()
        self._stream.close()

    def _seconds_to_chunks(self, seconds: float):
        if seconds <= 0:
            raise ValueError("seconds must be greater than 0")
        return max(1, math.ceil((seconds * self.RATE) / self.CHUNK_SIZE))

if __name__ == "__main__":
    import time

    reader = AudioReader()
    reader.start_recording()

    for _ in range(20):
        print(f"Volume: {reader.volume:.3f}")
        time.sleep(0.1)

    reader.close()
