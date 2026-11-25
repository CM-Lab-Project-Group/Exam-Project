
/** @type {HTMLVideoElement} */
const videoElement = document.getElementById("cameraPlayback");
/** @type {HTMLButtonElement} */
const recordingBtn = document.getElementById("recording-button");

/** @type {MediaStream | undefined} */
let cameraStream = undefined;
/** @type {MediaRecorder | undefined} */
let mediaRecorder = undefined;
/** @type {WebSocket | undefined} */
let socket = undefined;
/** @type {number | undefined} */
let cameraTimeoutId = undefined;

const CAMERA_IDLE_TIMEOUT_MS = 5000;
const CHUNK_INTERVAL_MS = 1000;

/**
 * 
 * @param {string} path 
 * @returns 
 */
function getWebSocketUrl(path) {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    return `${protocol}//${window.location.host}${path}`;
}

async function startCameraFeed() {
    if (cameraTimeoutId !== undefined) {
        clearTimeout(cameraTimeoutId);
        cameraTimeoutId = undefined;
    }

    if (cameraStream) return;

    cameraStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
    videoElement.srcObject = cameraStream;
    videoElement.parentElement.classList.add("on");

}

async function stopCamera() {
    console.log("Stopping stream!", cameraStream);
    if (!cameraStream) return;

    cameraStream.getTracks().forEach((track) => track.stop());
    videoElement.srcObject = null;
    videoElement.parentElement?.classList.remove("on");
    cameraStream = undefined;
}

async function startRecording() {
    await startCameraFeed();
    if (!cameraStream) return;

    socket = new WebSocket(getWebSocketUrl("/ws/record"));

    await new Promise((resolve, reject) => {
        socket.onopen = resolve;
        socket.onerror = (e) => reject(new Error("WebSocket connection failed", e));
    });

    socket.onmessage = (event) => {
        const info = JSON.parse(event.data);
        console.log("Recording to:", info.filename);
    };

    mediaRecorder = new MediaRecorder(cameraStream, { mimeType: "video/webm" });

    mediaRecorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0 && socket?.readyState === WebSocket.OPEN) {
            socket.send(event.data);
        }
    };

    mediaRecorder.start(CHUNK_INTERVAL_MS);
}

async function stopRecording() {
    if (!mediaRecorder || mediaRecorder.state === "inactive") return;

    const recorder = mediaRecorder;
    mediaRecorder = undefined;

    await new Promise((resolve) => {
        recorder.onstop = resolve;
        recorder.stop();
    });

    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.close(1000, "Recording complete");
    }
    socket = undefined;

    await stopCamera();
}

async function onRecordingButton() {
    const isRecording = recordingBtn.dataset["recording"] === "1";
    recordingBtn.disabled = true;
    console.log("Recording is " + isRecording ? "active" : "inactive");
    

    try {
        if (!isRecording) {
            await startRecording();
            recordingBtn.textContent = "Stop Recording";
            recordingBtn.dataset["recording"] = "1";
        } else {
            await stopRecording();
            recordingBtn.textContent = "Start Recording";
            recordingBtn.dataset["recording"] = "0";
        }
    } catch (err) {
        console.error("Recording error:", err);
        recordingBtn.dataset["recording"] = "0";
    } finally {
        recordingBtn.disabled = false;
    }
}

function main() {
    if (!MediaRecorder.isTypeSupported("video/webm")) {
        console.error("MediaRecorder is incapable of recording video/webm");
        return;
    }

    if (!"recording" in recordingBtn.dataset || !recordingBtn.dataset["recording"]) {
        recordingBtn.dataset["recording"] = "0";
    }

    recordingBtn.addEventListener("click", onRecordingButton);
}


main();