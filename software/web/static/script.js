/** @type {HTMLImageElement} */
const feedImage = document.getElementById("cameraPlayback");

/** @type {HTMLVideoElement} */
const playbackVideo = document.getElementById("recordedPlayback");

/** @type {HTMLButtonElement} */
const cameraBtn = document.getElementById("camera-button");
/** @type {HTMLButtonElement} */
const recordBtn = document.getElementById("record-button");

/** @type {HTMLUListElement} */
const recordingsList = document.getElementById("recordings-list");

const STATUS_POLL_INTERVAL_MS = 2500;

let isToggling = false;
let lastKnownRecording = false;

cameraBtn.turnOn = () => {
    cameraBtn.textContent = "Stop Camera";
    cameraBtn.dataset["active"] = "1";
}

cameraBtn.turnOff = () => {
    cameraBtn.textContent = "Start Camera";
    cameraBtn.dataset["active"] = "0";
}

cameraBtn.isActive = () => cameraBtn.dataset["active"] === "1";

recordBtn.turnOn = () => {
    recordBtn.textContent = "Stop Recording";
    recordBtn.dataset["active"] = "1";
}

recordBtn.turnOff = () => {
    recordBtn.textContent = "Start Recording";
    recordBtn.dataset["active"] = "0";
}

recordBtn.isActive = () => recordBtn.dataset["active"] === "1";


/** @param {boolean} disabled */
function setFeedControlsDisabledState(disabled) {
    cameraBtn.disabled = disabled;
    recordBtn.disabled = disabled;
}

/**
 * 
 * @param {string} url 
 * @returns {Promise<{ camera_on: boolean, recording: boolean }>}
 */
async function postJson(url) {
    const res = await fetch(url, { method: "POST", cache: "no-cache" });
    const data = await res.json();
    if (!res.ok) {
        throw new Error(data.error || `Request failed (${res.status})`);
    }
    return data;
}

function attachFeedStream() {
    if (feedImage.src && feedImage.src.includes("/video_feed")) return;
    feedImage.src = `/video_feed?t=${Date.now()}`;
}

function cacheBuster() {
    if (feedImage.src && feedImage.src.includes("/video_feed")) return;
    feedImage.src = `/video_feed?t=${Date.now()}`;
}

/** @param {boolean} isCameraOn */
function setCameraState(isCameraOn) {
    const parentClassList = feedImage.parentElement?.classList;

    if (isCameraOn) {
        attachFeedStream();
        parentClassList?.add("on");
        cameraBtn.turnOn();
    } else {
        feedImage.removeAttribute("src");
        parentClassList?.remove("on");
        cameraBtn.turnOff();
    }
}

/** @param {boolean} isRecording */
function setRecordingState(isRecording) {
    if (isRecording) {
        recordBtn.turnOn();
    } else {
        recordBtn.turnOff();
    }
}

/** @param {{ camera_on: boolean, recording: boolean }} state */
async function applyServerState(state) {
    const finishedRecording = lastKnownRecording && !state.recording;
    lastKnownRecording = state.recording;

    setCameraState(state.camera_on);
    setRecordingState(state.recording);

    if (finishedRecording) {
        await refreshRecordings();
    }
}

async function syncStatus() {
    if (isToggling) return;

    try {
        const res = await fetch("/api/status", { cache: "no-cache" });
        if (!res.ok) return;
        await applyServerState(await res.json());
    } catch (e) {
        console.error("Status sync failed:", e);
    }
}

async function refreshRecordings() {
    const res = await fetch("/api/recordings", { cache: "no-cache" });
    if (!res.ok) return;

    /** @type {string[]} */
    const files = await res.json();
    recordingsList.innerHTML = "";

    for (const filename of files) {
        const li = document.createElement("li");
        const btn = document.createElement("button");
        btn.type = "button";
        btn.textContent = `> ${filename}`;
        btn.addEventListener("click", () => {
            playbackVideo.src = `/stream/${encodeURIComponent(filename)}`;
            playbackVideo.play();
        });
        li.appendChild(btn);
        recordingsList.appendChild(li);
    }
}

async function sendToggleRequest(endpoint) {
    isToggling = true;
    setFeedControlsDisabledState(true);

    try {
        const state = await postJson(endpoint);
        await applyServerState(state);
    } catch (e) {
        console.error("Control request error:", e);
        isToggling = false;
        await syncStatus();
    } finally {
        isToggling = false;
        setFeedControlsDisabledState(false);
    }
}

async function onCameraToggleButton() {
    const endPoint = "/api/camera/" + (cameraBtn.isActive() ? "stop" : "start");
    await sendToggleRequest(endPoint);
}

async function onRecordToggleButton() {
    const endPoint = "/api/record/" + (recordBtn.isActive() ? "stop" : "start");
    await sendToggleRequest(endPoint);
}

async function main() {
    cameraBtn.addEventListener("click", async () => await onCameraToggleButton());
    recordBtn.addEventListener("click", async () => await onRecordToggleButton());

    const res = await fetch("/api/status", { cache: "no-cache" });
    if (res.ok) {
        applyServerState(await res.json());
    }

    await syncStatus();
    await refreshRecordings();
    setFeedControlsDisabledState(false);

    window.setInterval(syncStatus, STATUS_POLL_INTERVAL_MS);
}

main();