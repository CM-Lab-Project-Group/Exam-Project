/** @type {HTMLImageElement} */
const feedImage = document.getElementById("cameraPlayback");
/** @type {HTMLMeterElement} */
const volumeMeter = document.getElementById("volume-meter");

/** @type {HTMLVideoElement} */
const playbackVideo = document.getElementById("recordedPlayback");
/** @type {HTMLVideoElement} */
const playbackAudio = document.getElementById("audioPlayback");

/** @type {HTMLButtonElement} */
const cameraBtn = document.getElementById("camera-button");
/** @type {HTMLButtonElement} */
const recordBtn = document.getElementById("record-button");
/** @type {HTMLButtonElement} */
const audioSaveBtn = document.getElementById("audio-save-button");

/** @type {HTMLUListElement} */
const recordingsList = document.getElementById("recordings-list");
/** @type {HTMLUListElement} */
const audioList = document.getElementById("audio-list");

const webSocket = new WebSocket(`ws://${location.hostname}:8765`);

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

/** @param {boolean} isCameraOn */
function setCameraState(isCameraOn) {
    const parentClassList = feedImage.parentElement?.classList;

    if (isCameraOn) {
        attachFeedStream();
        parentClassList?.add("on");
        cameraBtn.turnOn();
    } else {
        renderTestImage();
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

/** @param {{ camera_on: boolean, recording: boolean, volume: number, image_size: { width: number, height: number } }} state */
async function applyServerState(state) {
    const finishedRecording = lastKnownRecording && !state.recording;
    lastKnownRecording = state.recording;

    setCameraState(state.camera_on);
    setRecordingState(state.recording);
    setVolume(state.volume);

    if (finishedRecording) {
        await refreshRecordings();
    }
}

/** @param {number} volume */
async function setVolume(volume) {
    if (!volumeMeter) return;
    if (volume === undefined) volume = 0;
    volumeMeter.value = Math.round(volume);
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

/**
 * 
 * @param {HTMLUListElement} ulElem 
 * @param {string[]} filenames 
 * @returns {HTMLButtonElement[]}
 */
function populateRecordingsList(ulElem, filenames) {
    ulElem.innerHTML = "";

    /** @type {HTMLButtonElement[]} */
    const btns = [];

    for (const filename of filenames) {
        const li = document.createElement("li");
        const btn = document.createElement("button");
        btn.type = "button";
        btn.textContent = `> ${filename}`
        btn.dataset.filename = `${filename}`
        const btnNode = li.appendChild(btn);
        btns.push(btnNode);
        ulElem.appendChild(li);
    }

    return btns;
}

async function refreshRecordings() {
    const res = await fetch("/api/recordings", { cache: "no-cache" });
    if (!res.ok) return;

    /** @type {{ video: string[], audio: string[] }} */
    const payload = await res.json();

    const video_file_buttons = populateRecordingsList(recordingsList, payload.video);
    const audioFileButtons = populateRecordingsList(audioList, payload.audio);

    video_file_buttons.forEach((btn) => {
        btn.addEventListener("click", () => {
            const file = btn.dataset.filename;
            playbackVideo.src = `/stream/video/${file}`;
            playbackVideo.play();
        });
    })
    audioFileButtons.forEach((btn) => {
        btn.addEventListener("click", () => {
            const file = btn.dataset.filename;
            playbackAudio.src = `/stream/audio/${file}`;
            playbackAudio.play();
        });
    })
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

async function saveAudio() {
    const response = await fetch("/api/audio/save", { method: "POST" });
    const filename = await response.text();
    console.log(`Saved as "${filename}"`)
}

function renderTestImage() {
    const canvas = document.createElement("canvas");
    canvas.width = feedImage.width
    canvas.height = feedImage.height

    const ctx = canvas.getContext("2d");

    ctx.fillStyle = "red";
    ctx.fillRect(0, 0, canvas.width / 2, canvas.height / 2);
    ctx.fillStyle = "blue";
    ctx.fillRect(canvas.width / 2, canvas.height / 2, canvas.width, canvas.height);

    const url = canvas.toDataURL();
    console.log(url);
    feedImage.src = url;
}

async function main() {
    cameraBtn.addEventListener("click", onCameraToggleButton);
    recordBtn.addEventListener("click", onRecordToggleButton);
    audioSaveBtn.addEventListener("click", saveAudio);

    const res = await fetch("/api/status", { cache: "no-cache" });
    if (res.ok) {
        applyServerState(await res.json());
    }

    webSocket.addEventListener("message", (ev) => {
        /** @type {{camera_on: boolean, recording: boolean, volume: number}} */
        const payload = JSON.parse(ev.data);
        applyServerState(payload);
    });

    await refreshRecordings();
    setFeedControlsDisabledState(false);

    renderTestImage();
}

main();