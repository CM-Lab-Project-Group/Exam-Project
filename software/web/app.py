import json
import os
import time
import threading
import datetime
import cv2
from pathlib import Path
from flask import Flask, Response, send_file, send_from_directory, jsonify, request, session
from werkzeug.utils import secure_filename

def megabytes_to_bytes(megabytes: int):
    return megabytes * 1024 * 1024

MAX_CHUNK_BYTES = megabytes_to_bytes(10)
MAX_RECORDING_BYTES = megabytes_to_bytes(500)
WEBM_MAGIC_HEADER = b"\x1a\x45\xdf\xa3"

app = Flask(__name__)
PORT = 8080

app.secret_key = os.urandom(32)
app.config["MAX_CONTENT_LENGTH"] = megabytes_to_bytes(10)

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

RECORDINGS_DIR = DATA_DIR / "recordings"
RECORDINGS_DIR.mkdir(exist_ok=True)

active_recordings = {}


class ServerCamera:
    def __init__(self, device_index: int = 0, target_fps: float = 30) -> None:
        self.device_index = device_index
        self.target_fps = target_fps

        self._lock = threading.Lock()
        self._frame_ready = threading.Condition(self._lock)

        self._capture: cv2.VideoCapture | None = None
        self._writer: cv2.VideoWriter | None = None
        self._thread: threading.Thread | None = None

        self._running = False
        self._recording = False
        self._current_file: str | None = None
        self._latest_jpeg: bytes | None = None
        self._frame_id = 0
        self._width = 640
        self._height = 480

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._running

    @property
    def is_recording(self) -> bool:
        with self._lock:
            return self._recording

    def status(self) -> dict:
        with self._lock:
            return {
                "camera_on": self._running,
                "recording": self._recording,
                "filename": self._current_file
            }

    def start_camera(self) -> None:
        with self._lock:
            self._start_camera()

    def stop_camera(self) -> None:
        with self._lock:
            thread = self._stop_camera_thread()

        if thread is not None:
            thread.join(timeout=2.0)

        with self._lock:
            thread = self._stop_camera_capture()

    def start_recording(self) -> str:
        with self._lock:
            return self._start_recording()

    def stop_recording(self) -> str | None:
        with self._lock:
            return self._stop_recording()

    def stream_mjpeg(self):
        last_seen_id = -1

        while True:
            with self._frame_ready:
                while (self._running and self._frame_id == last_seen_id):
                    self._frame_ready.wait(timeout=1.0)

                if not self._running:
                    break

                frame_bytes = self._latest_jpeg
                last_seen_id = self._frame_id

            if frame_bytes is None:
                continue

            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
            )

    def _start_camera(self) -> None:
        if self._running:
            return

        cap = cv2.VideoCapture(self.device_index)
        if not cap.isOpened():
            raise RuntimeError(f"Could not open camera device {self.device_index}")

        self._width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
        self._height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480
        self._capture = cap
        self._running = True
        self._latest_jpeg = None

        self._thread = threading.Thread(target=self._capture_loop)
        self._thread.start()

    def _stop_camera_thread(self) -> threading.Thread | None:
        if not self._running:
            return

        self._running = False
        self._frame_ready.notify_all()
        thread = self._thread
        self._thread = None
        return thread

    def _stop_camera_capture(self) -> None:
        if self._capture is not None:
            self._capture.release()
            self._cap = None
        self._latest_jpeg = None

    def _start_recording(self) -> str:
        if self._recording and self._current_file:
            return self._current_file

        timestamp = int(time.time() * 1000)
        candidates = [
            (f"rec_${timestamp}.mp4", cv2.VideoWriter.fourcc(*"avc1")),
            (f"rec_${timestamp}.webm", cv2.VideoWriter.fourcc(*"VP80")),
        ]

        writer = None
        filename = None

        for candiate_name, fourcc in candidates:
            file_path = RECORDINGS_DIR / candiate_name
            w = cv2.VideoWriter(
                str(file_path),
                fourcc,
                self.target_fps,
                (self._width, self._height),
            )
            if w.isOpened():
                writer = w
                filename = candiate_name
                break

            w.release()
            file_path.unlink(missing_ok=True)

        if writer is None or filename is None:
            raise RuntimeError("Failed to initialize browser-compatible VideoWriter")

        self._writer = writer
        self._current_file = filename
        self._recording = True
        return filename

    def _stop_recording(self) -> str | None:
        if not self._recording:
            return None

        finished_file = self._current_file
        self._recording = False
        self._current_file = None

        if self._writer is not None:
            self._writer.release()
            self._writer = None

        return finished_file

    def _draw_overlay(self, frame, is_recording: bool) -> None:
        now = datetime.datetime.now()
        BOX_PADDING = 2
        FONT_FACE = cv2.FONT_HERSHEY_SIMPLEX
        FONT_SCALE = .65
        FONT_THICKNESS = 2
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S")

        (text_width, text_height), baseLine = cv2.getTextSize(timestamp, FONT_FACE, FONT_SCALE, FONT_THICKNESS);
        
        cv2.rectangle(
            frame,
            (12, self._height - 42),
            (145, self._height - 12),
            (0, 0, 0),
            -1
        )
        cv2.putText(
            frame,
            timestamp,
            (20, self._height - 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )

        if is_recording and int(time.time()) % 2 == 0:
            cv2.circle(frame, (self._width - 75, 28), 7, (0, 0, 239), -1)
            cv2.putText(
                frame,
                "REC",
                (self._width - 60, 34),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )

    def _capture_loop(self) -> None:
        frame_interval = 1.0 / self.target_fps

        while True:
            loop_start = time.monotonic()

            with self._lock:
                if not self._running or self._capture is None:
                    break
                cap = self._capture
                recording = self._recording

            ok, frame = cap.read()
            if not ok:
                time.sleep(0.05)
                continue

            self._draw_overlay(frame, recording)

            ok_jpg, buffer = cv2.imencode(
                ".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80]
            )

            with self._lock:
                if self._recording and self._writer is not None:
                    self._writer.write(frame)

                if ok_jpg:
                    self._latest_jpeg = buffer.tobytes()
                    self._frame_id += 1
                    self._frame_ready.notify_all()

            elapsed = time.monotonic() - loop_start
            if elapsed < frame_interval:
                time.sleep(frame_interval - elapsed)


camera = ServerCamera(0, target_fps=30.0)

@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.get("/api/status")
def get_status():
    return jsonify(camera.status())


@app.post("/api/camera/start")
def start_upload():
    try:
        camera.start_camera()
        return jsonify(camera.status()), 200
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 500

@app.post("/api/camera/stop")
def api_camera_stop():
    camera.stop_camera()
    return jsonify(camera.status()), 200

@app.post("/api/record/start")
def api_start_recording():
    try:
        camera.start_recording()
        return jsonify(camera.status()), 200
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 500

@app.post("/api/record/stop")
def api_stop_recording():
    finished = camera.stop_recording()
    return jsonify({**camera.status(), "saved_file": finished}), 200

@app.get("/video_feed")
def video_feed():
    if not camera.is_running:
        return "Camera is off", 409

    return Response(
        camera.stream_mjpeg(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )

@app.get("/api/recordings")
def get_recordings():
    files = [f for f in RECORDINGS_DIR.glob("*.webm") if f.is_file()]
    files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    return jsonify([file.name for file in files])


@app.get("/stream/<filename>")
def stream_video(filename):
    safe_name = secure_filename(filename)
    file_path = RECORDINGS_DIR / safe_name
    if not file_path.is_file():
        return "Recording not found", 404

    return send_file(
        str(file_path.absolute()),
        mimetype="video/webm",
        conditional=True,
    )

@app.get("/<path:path>")
def serve_static_file(path):
    return send_from_directory("static", path)

if __name__ == "__main__":
    app.run(port=PORT, debug=True, use_reloader=False)