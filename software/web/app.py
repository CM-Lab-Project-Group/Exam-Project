import json
import os
import time
import datetime
from pathlib import Path
from flask import Flask, send_file, send_from_directory, redirect, url_for, jsonify, request
from flask_sock import Sock, Server
from simple_websocket import ConnectionClosed
from werkzeug.utils import secure_filename

def megabytes_to_bytes(megabytes: int):
    return megabytes * 1024 * 1024


app = Flask(__name__)
PORT = 8080

sock = Sock(app)

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

RECORDINGS_DIR = DATA_DIR / "recordings"
RECORDINGS_DIR.mkdir(exist_ok=True)

active_recordings = {}


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/recordings", methods=["GET"])
def get_recordings():
    files: list[Path] = []
    for file in RECORDINGS_DIR.glob(("*.webp")):
        if not file.exists() or not file.is_file():
            continue
        files.append(file)
    files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    return jsonify([file.name for file in files])


@app.get("/stream/<filename>")
def stream_video(filename):
    safe_name = secure_filename(filename)
    file_path = RECORDINGS_DIR / safe_name
    if not file_path.exists():
        return "Recording not found", 404

    return send_file(
        str(file_path.absolute()),
        mimetype="video/webm",
        conditional=True
    )

@sock.route("/ws/record")
def record_stream(ws: Server):
    filename = f"rec_{int(time.time() * 1000)}.webm"
    file_path = RECORDINGS_DIR / filename

    ws.send(json.dumps({"filename": filename}))

    with file_path.open("wb") as f:
        try:
            while True:
                chunk = ws.receive()
                if isinstance(chunk, (bytes, bytearray)):
                    f.write(chunk)
                    f.flush()
        except ConnectionClosed:
            pass


@app.get("/<path:path>")
def serve_static_file(path):
    return send_from_directory("static", path)

if __name__ == "__main__":
    app.run(port=PORT, debug=True)