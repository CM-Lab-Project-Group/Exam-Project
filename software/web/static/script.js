
/** @type {HTMLVideoElement} */
const videoElement = document.getElementById("cameraPlayback");
/** @type {HTMLButtonElement} */
const cameraBtn = document.getElementById("recording-button");
/** @type {HTMLInputElement} */
const recordingCheckbox = document.getElementById("record-checkbox");

const sourceVideo = document.createElement("video");
sourceVideo.muted = true;
sourceVideo.playsInline = true;

const canvas = document.createElement("canvas");
const ctx = canvas.getContext("2d");

/** @type {MediaStream | undefined} */
let cameraStream = undefined;
/** @type {MediaStream | undefined} */
let compositeStream = undefined;
/** @type {MediaRecorder | undefined} */
let mediaRecorder = undefined;
/** @type {number | undefined} */
let cameraTimeoutId = undefined;
/** @type {number | undefined} */
let renderLoopId = undefined;

let recBlink = false;
/** @type {number | undefined} */
let recBlinkIntervalId = undefined;

/** @type {Promise | undefined} */
let uploadChain = undefined;

const CHUNK_INTERVAL_MS = 1000;
const TARGET_FPS = 30;

/**
 * Draws information onto a canvas
 * @param {CanvasRenderingContext2D} context 
 * @param {number} width 
 * @param {number} height 
 */
function drawOverlay(context, width, height) {
    const fontSize = Math.max(12, Math.round(height * 0.04));
    const pad = Math.round(fontSize * 0.45);
    const margin = Math.round(height * 0.03);

    const timestamp = new Date().toLocaleTimeString();
    context.font = `bold ${fontSize}px monospace`;
    context.textBaseline = "middle";

    const textWidth = context.measureText(timestamp).width;
    const boxWidth = textWidth + pad * 2;
    const boxHeight = fontSize + pad * 1.4;
    const boxX = margin;
    const boxY = height - margin - boxHeight;

    context.fillStyle = "rgba(0, 0, 0, .55)";
    context.fillRect(boxX, boxY, boxWidth, boxHeight);


    context.fillStyle = "#fff";
    context.fillText(timestamp, boxX + pad, boxY + boxHeight / 2);

    if (mediaRecorder && mediaRecorder.state === "recording" && recBlink) {
        const badgeFontSize = Math.round(fontSize * 0.05);
        const dotRadius = Math.round(badgeFontSize * 0.4);
        context.font = `bold ${badgeFontSize}px sans-serif`;

        const labelWidth = context.measureText("REC").width;
        const textX = width - margin - labelWidth;
        const centerY = margin + badgeFontSize / 2;

        context.fillStyle = "#ef4444";
        context.beginPath();
        context.arc(textX - dotRadius * 1.8, centerY, dotRadius, 0, Math.PI * 2);
        context.fill();

        context.fillStyle = "#ffffff";
        context.fillText("REC", textX, centerY);
    }
}

function startRenderLoop() {
    if (!ctx) return;

    const renderFrame = () => {
        if (sourceVideo.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA) {
            ctx.drawImage(sourceVideo, 0, 0, canvas.width, canvas.height);
            drawOverlay(ctx, canvas.width, canvas.height);
        }
        renderLoopId = requestAnimationFrame(renderFrame);
    };

    recBlinkIntervalId = setInterval(() => recBlink = !recBlink, 1000);
    renderLoopId = requestAnimationFrame(renderFrame);
}

function stopRenderLoop() {
    if (renderLoopId === undefined) return;

    clearInterval(recBlinkIntervalId);
    recBlinkIntervalId = undefined;

    recBlink = false;

    cancelAnimationFrame(renderLoopId);
    renderLoopId = undefined;
}

async function startCameraStream() {
    if (compositeStream) return;

    cameraStream = await navigator.mediaDevices.getUserMedia({ video: true });
    sourceVideo.srcObject = cameraStream;
    await sourceVideo.play();

    canvas.width = sourceVideo.videoWidth || 640;
    canvas.height = sourceVideo.videoHeight || 480;
    
    startRenderLoop();
    compositeStream = canvas.captureStream(TARGET_FPS);
}

function updateStreamDisplay() {
    const isActive = Boolean(cameraStream && cameraStream.active);
    videoElement.srcObject = isActive ? compositeStream : null;
    
    const parentClassList = videoElement.parentElement.classList;
    if (isActive) {
        parentClassList.add("on");
    } else {
        parentClassList.remove("on");
    }

}

/** @param {MediaStream} mediaStream  */
function stopAllMediaTracks(mediaStream) {
    mediaStream.getTracks().forEach(track => track.stop());
}


function stopCameraStream() {
    stopRenderLoop();

    if (compositeStream) {
        stopAllMediaTracks(compositeStream);
        compositeStream = undefined;
    }

    if (cameraStream) {
        stopAllMediaTracks(cameraStream);
        cameraStream = undefined;
    }

    sourceVideo.srcObject = null;
}


async function startFeed() {
    await startCameraStream();
    updateStreamDisplay();
}

function stopCamera() {
    stopCameraStream();
    updateStreamDisplay();
}


/**
 * @param {BlobEvent} ev 
*/
async function mediaRecorderDataAvailable(ev) {
    const blob = ev.data;
    if (!blob || blob.size == 0) return;

    uploadChain = uploadChain.then(async () => {
        const res = await fetch("/upload/chunk", {
            method: "POST",
            body: blob,
            cache: "no-cache",
        });
        if (!res.ok) {
            throw new Error(`Chunk upload failed with status code ${res.status}`);
        }
    })

}

/** @returns {Promise<boolean>} */
async function requestUploadStart() {
    return (await fetch("/upload/start", { method: "POST", cache: "no-cache" })).ok;
}

async function startRecording() {
    await startFeed();

    if (!compositeStream) return;
    if (!cameraStream) return;

    if (!await requestUploadStart()) {
        throw new Error("Upload has been denied");
    }


    mediaRecorder = new MediaRecorder(compositeStream, { mimeType: "video/webm" });

    uploadChain = Promise.resolve();
    mediaRecorder.addEventListener("dataavailable", mediaRecorderDataAvailable);
    mediaRecorder.start(CHUNK_INTERVAL_MS);
}

async function stopRecording() {
    if (!mediaRecorder || mediaRecorder.state === "inactive") return;
    
    const recorder = mediaRecorder;
    mediaRecorder = undefined;
    
    await stopRecorder(recorder);
    recorder.removeEventListener("dataavailable", mediaRecorderDataAvailable);
    await uploadChain;
    uploadChain = undefined;

    stopCamera();
}

/**
 * @param {MediaRecorder} recorder 
 */
function stopRecorder(recorder) {
    return new Promise((resolve, reject) => {
        recorder.addEventListener("stop", resolve, { once: true });
        recorder.addEventListener("error", reject, { once: true });
        recorder.stop();
    });
}

/** @param {boolean} recordingState */
function setRecordingState(recordingState) {
    cameraBtn.textContent = (recordingState ? "Stop" : "Start") + " Recording";
    cameraBtn.dataset["recording"] = recordingState ? "1" : "0";
}

async function onCameraToggleButton() {
    const isCapturing = cameraBtn.dataset["recording"] === "1";
    cameraBtn.disabled = true;
    console.log("Recording is " + (isCapturing ? "active" : "inactive"));
    
    try {
        const changePromise = isCapturing ? stopRecording() : startRecording();
        await changePromise;
        setRecordingState(!isCapturing);
    } catch (err) {
        console.error("Recording error:", err);
        setRecordingState(false);
    } finally {
        cameraBtn.disabled = false;
    }
}

async function onCheckboxChangeRequest() {
    
}

function main() {
    if (!MediaRecorder.isTypeSupported("video/webm")) {
        console.error("MediaRecorder is incapable of recording video/webm");
        return;
    }

    if (!cameraBtn.dataset["recording"]) {
        cameraBtn.dataset["recording"] = "0";
    }

    cameraBtn.addEventListener("click", onCameraToggleButton);
    recordingCheckbox.addEventListener("change", onCheckboxChangeRequest);
}


main();