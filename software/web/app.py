import json
import os
import time
import datetime
from pathlib import Path
from flask import Flask, send_file, send_from_directory, redirect, url_for, jsonify, request, session
from flask_sock import Sock, Server
from simple_websocket import ConnectionClosed
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

@app.post("/upload/start")
def start_upload():
    filename = f"rec_{int(time.time() * 1000)}.webm"
    file_path = RECORDINGS_DIR / filename
    with file_path.open("wb",) as f:
        f.flush()
    set_filename_session(filename)
    return str(filename), 200

def set_filename_session(filename: str | None):
    SESSION_FILE_KEY = "recording_filename"
    if filename is None:
        session.pop(SESSION_FILE_KEY, None)
    session[SESSION_FILE_KEY] = filename

def get_session_filename() -> str | None:
    SESSION_FILE_KEY = "recording_filename"
    if not SESSION_FILE_KEY in session:
        return None
    return session.get(SESSION_FILE_KEY, None)


@app.post("/upload/chunk")
def upload_chunk():
    raw_filename = get_session_filename()
    if not raw_filename:
        return jsonify({ "error": "Please call /upload/start first" }), 400

    safe_name = secure_filename(raw_filename)
    file_path = RECORDINGS_DIR / safe_name

    chunk = request.get_data()
    if not chunk:
        return jsonify({ "error": "Empty chunk" }), 400

    current_size = file_path.stat().st_size

    if current_size == 0 and not chunk.startswith(WEBM_MAGIC_HEADER):
        file_path.unlink(missing_ok=True)
        session.pop("recording_filename", None)
        return jsonify({"error": "Invalid WebM stream"}), 415

    if current_size + len(chunk) > MAX_RECORDING_BYTES:
        session.pop("recording_filename", None)
        return jsonify({ "error": "Maximum recording size exeeded" }), 413

    with file_path.open("ab") as f:
        f.write(chunk)
    
    return "", 204


@app.get("/<path:path>")
def serve_static_file(path):
    return send_from_directory("static", path)

if __name__ == "__main__":
    app.run(port=PORT, debug=True)