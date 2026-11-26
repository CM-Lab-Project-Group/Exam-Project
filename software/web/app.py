import asyncio
import json
import os
from pathlib import Path
import threading
from typing import Iterator
from audioManagement import AudioReader, AUDIO_RECORDINGS_DIR
from flask import Flask, Response, send_file, send_from_directory, jsonify, request
from werkzeug.utils import secure_filename
import websockets.asyncio.server as async_wss

from videoStreaming import ServerCamera, RECORDINGS_DIR

def megabytes_to_bytes(megabytes: int):
    return megabytes * 1024 * 1024

app = Flask(__name__)
CONNECTED_CLIENTS = set()
PORT = 8080

app.secret_key = os.urandom(32)
app.config["MAX_CONTENT_LENGTH"] = megabytes_to_bytes(10)


active_recordings = {}


camera = ServerCamera(0, target_fps=30.0)
audio = AudioReader(2)


async def ws_handler(websocket: async_wss.ServerConnection):
    CONNECTED_CLIENTS.add(websocket)
    try:
        async for message in websocket:
            data = json.loads(message)
            if data.get("action", "") == "save":
                audio.save_wav()
    finally:
        CONNECTED_CLIENTS.discard(websocket)

def assemble_status_dict() -> dict:
    camera_status = camera.status()
    device = audio.input_device[0]
    return {
        "volume": audio.volume_percent,
        "device": device["name"],
        "camera_on": camera_status.camera_on,
        "recording": camera_status.recording,
        "image_size": {
            "width": camera_status.image_size[0],
            "height": camera_status.image_size[1]
        }
    }

async def broadcast_status():
    while True:
        if CONNECTED_CLIENTS:
            payload = json.dumps(assemble_status_dict())
            async_wss.broadcast(CONNECTED_CLIENTS, payload)
        await asyncio.sleep(.1)

async def run_ws_server():
    async with async_wss.serve(ws_handler, "127.0.0.1", 8765):
        await broadcast_status()

def start_ws_background_thread():
    thread = threading.Thread(
        target=lambda: asyncio.run(run_ws_server()),
        daemon=True
    )
    thread.start()

@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.get("/api/status")
def get_status():
    app.logger.info("Sending status")
    return jsonify(assemble_status_dict()), 200

@app.get("/api/audio/volume")
def get_volume():
    return jsonify({"volume": audio.volume}), 200

@app.post("/api/audio/save")
def save_audio():
    filename = audio.save_wav()
    return filename, 200

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
    return jsonify({**camera.status().__dict__, "saved_file": finished}), 200

@app.get("/video_feed")
def video_feed():
    if not camera.is_running:
        return "Camera is off", 409

    return Response(
        camera.stream_mjpeg(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )

def sort_by_modified_time(file: Path):
    return file.stat().st_mtime

def get_recording_filenames(iterator: Iterator[Path]) -> list[str]:
    files = [f for f in iterator if f.is_file()]
    files.sort(key=sort_by_modified_time, reverse=True)
    return [file.name for file in files]


@app.get("/api/recordings")
def get_recordings():
    data = {
        "video": get_recording_filenames(RECORDINGS_DIR.glob("*.webm")),
        "audio": get_recording_filenames(AUDIO_RECORDINGS_DIR.glob("*.wav")),
    }
    return jsonify(data)

@app.get("/stream/video/<filename>")
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

@app.get("/stream/audio/<filename>")
def stream_audio(filename):
    safe_name = secure_filename(filename)
    file_path = AUDIO_RECORDINGS_DIR / safe_name
    if not file_path.is_file():
        return "Recording not found", 404

    return send_file(
        str(file_path.absolute()),
        mimetype="audio/wav",
        conditional=True
    )

@app.get("/<path:path>")
def serve_static_file(path):
    return send_from_directory("static", path)

if __name__ == "__main__":
    audio.start_recording()

    if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        start_ws_background_thread()

    app.run(port=PORT, debug=True, use_reloader=False)