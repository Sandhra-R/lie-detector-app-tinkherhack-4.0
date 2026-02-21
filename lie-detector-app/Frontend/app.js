const socket = io();
console.log('Socket.IO initialized, connecting...');

const video = document.getElementById('video');
video.muted = true; // Mute video element to avoid audio issues
const canvas = document.getElementById('canvas');
const startBtn = document.getElementById('startBtn');
const stopBtn = document.getElementById('stopBtn');
const resetBtn = document.getElementById('resetBtn');
const recordAudioBtn = document.getElementById('recordAudio');
const audioPlayback = document.getElementById('audioPlayback');

const blinkCountEl = document.getElementById('blinkCount');
const earValueEl = document.getElementById('earValue');
const pitchValueEl = document.getElementById('pitchValue');
const truthIndicatorEl = document.getElementById('truthIndicator');
const stressLevelEl = document.getElementById('stressLevel');
const stressProgressEl = document.getElementById('stressProgress');

let isStreaming = false;
let mediaRecorder;
let audioChunks = [];
let sendInterval = 200; // ms between frames (~5 fps)
let lastSend = 0;
let testMode = false; // Flag for demo mode without camera

startBtn.addEventListener('click', startCamera);
stopBtn.addEventListener('click', stopCamera);
resetBtn.addEventListener('click', async () => {
    try {
        await fetch('/reset', { method: 'POST' });
        blinkCountEl.textContent = '0';
        earValueEl.textContent = '0.00';
        pitchValueEl.textContent = '--';
        stressLevelEl.textContent = 'Ready';
        stressLevelEl.className = 'stress-indicator';
        stressProgressEl.style.width = '0%';
    } catch (err) {
        console.error('Reset error', err);
    }
});

recordAudioBtn.addEventListener('pointerdown', startRecording);
recordAudioBtn.addEventListener('pointerup', stopRecording);
recordAudioBtn.addEventListener('pointerleave', () => { if (mediaRecorder && mediaRecorder.state === 'recording') stopRecording(); });

socket.on('connect', () => {
    console.log('✓ Connected to server via Socket.IO');
});

socket.on('disconnect', () => {
    console.warn('⚠ Disconnected from server');
});

socket.on('connect_error', (error) => {
    console.error('Socket connection error:', error);
});

socket.on('analysis_result', (data) => {
    console.log('Received analysis result:', data);
    if (!data) {
        console.warn('Empty analysis result');
        return;
    }
    if (data.error) {
        console.warn('Backend error:', data.error);
        return;
    }

    // Show demo mode warning if applicable
    if (data.demo_mode) {
        document.getElementById('demoBanner').style.display = 'block';
    }

    if (typeof data.blink_count !== 'undefined') {
        blinkCountEl.textContent = data.blink_count;
    }
    if (typeof data.ear !== 'undefined') {
        earValueEl.textContent = Number(data.ear).toFixed(2);
    }
    if (typeof data.stress_level !== 'undefined') {
        const level = data.stress_level;
        stressLevelEl.textContent = level.toUpperCase() + (data.demo_mode ? ' (sim)' : '');
        stressLevelEl.className = `stress-indicator ${level}`;
        const pct = level === 'low' ? 20 : level === 'medium' ? 60 : 100;
        stressProgressEl.style.width = pct + '%';
    }
    if (typeof data.truth_indicator !== 'undefined') {
        truthIndicatorEl.textContent = data.truth_indicator + ' (' + (data.truth_likelihood || 0).toFixed(2) + ')';
    }
    // Facial expression
    const expressionEl = document.getElementById('expressionValue');
    if (expressionEl && typeof data.expression !== 'undefined') {
        expressionEl.textContent = data.expression;
        expressionEl.style.color = data.expression === 'neutral' ? '#2ed573' : '#ffa502';
    }
    // Gaze detection
    const gazeEl = document.getElementById('gazeValue');
    if (gazeEl && typeof data.gaze_shift !== 'undefined') {
        gazeEl.textContent = data.gaze_shift ? '⚠️ Shifting' : '✅ Steady';
        gazeEl.style.color = data.gaze_shift ? '#ff4757' : '#2ed573';
    }
    // Eyebrow
    if (typeof data.eyebrow_raised !== 'undefined') {
        console.log('[Video] Eyebrow raised:', data.eyebrow_raised, '| Mouth tension:', data.mouth_tension);
    }
});

async function startCamera() {
    try {
        console.log('Requesting camera and microphone access...');
        const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
        console.log('✓ Camera stream obtained:', stream);
        video.srcObject = stream;
        testMode = false;

        // Setup audio recording
        mediaRecorder = new MediaRecorder(stream);
        mediaRecorder.ondataavailable = (e) => audioChunks.push(e.data);
        mediaRecorder.onstop = onAudioStop;

        isStreaming = true;
        startBtn.disabled = true;
        stopBtn.disabled = false;
        console.log('✓ Streaming started, video frames will be sent every', sendInterval, 'ms');

        requestAnimationFrame(loop);
    } catch (err) {
        console.warn('Camera access denied or unavailable:', err.message);
        console.log('Falling back to TEST MODE - simulating video frames for demo');
        testMode = true;
        
        // Setup test mode: create a canvas-based video source
        const testCanvas = document.createElement('canvas');
        testCanvas.width = 640;
        testCanvas.height = 480;
        
        isStreaming = true;
        startBtn.disabled = true;
        stopBtn.disabled = false;
        console.log('✓ Test mode streaming started - frames will be sent every', sendInterval, 'ms');
        
        requestAnimationFrame(loop);
    }
}

function stopCamera() {
    const stream = video.srcObject;
    if (stream) stream.getTracks().forEach(track => track.stop());
    video.srcObject = null;
    isStreaming = false;
    startBtn.disabled = false;
    stopBtn.disabled = true;
}

function loop(ts) {
    if (!isStreaming) return;
    if (!lastSend) lastSend = ts;
    if (ts - lastSend >= sendInterval) {
        sendFrame();
        lastSend = ts;
    }
    requestAnimationFrame(loop);
}

function sendFrame() {
    const ctx = canvas.getContext('2d');
    
    if (testMode) {
        // In test mode, generate a test pattern image
        canvas.width = 640;
        canvas.height = 480;
        
        // Draw test pattern
        ctx.fillStyle = '#1a1a2e';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        
        // Draw some animated rectangles to simulate face
        const time = Date.now() / 1000;
        ctx.fillStyle = '#00d4ff';
        ctx.fillRect(150 + Math.sin(time) * 10, 100, 340, 280);
        
        ctx.fillStyle = '#7b2cbf';
        ctx.fillRect(200 + Math.sin(time * 1.5) * 5, 150, 80, 80);
        ctx.fillRect(360 + Math.sin(time * 1.5 + 1) * 5, 150, 80, 80);
        
        console.log('[TEST MODE] Sending synthetic frame');
    } else if (video.videoWidth && video.videoHeight) {
        // Normal camera mode
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        console.log('Sending video frame:', video.videoWidth, 'x', video.videoHeight);
    } else {
        console.warn('Video element not ready:', video.videoWidth, 'x', video.videoHeight);
        return;
    }
    
    const imageData = canvas.toDataURL('image/jpeg', 0.6);
    socket.emit('video_frame', { image: imageData });
}

function startRecording() {
    if (!mediaRecorder) return;
    audioChunks = [];
    try { mediaRecorder.start(); } catch (e) { console.warn(e); }
    recordAudioBtn.textContent = 'Recording...';
}

function stopRecording() {
    if (!mediaRecorder) return;
    try { mediaRecorder.stop(); } catch (e) { console.warn(e); }
    recordAudioBtn.textContent = 'Hold to Record Voice';
}

async function onAudioStop() {
    let audioBlob = new Blob(audioChunks, { type: audioChunks[0]?.type || 'audio/webm' });
    // Convert non-wav blobs to WAV for server compatibility
    if (!audioBlob.type.includes('wav') && typeof AudioContext !== 'undefined') {
        try {
            audioBlob = await convertBlobToWav(audioBlob);
        } catch (err) {
            console.warn('WAV conversion failed, sending original blob:', err);
        }
    }

    const audioUrl = URL.createObjectURL(audioBlob);
    audioPlayback.src = audioUrl;

    const formData = new FormData();
    formData.append('audio', audioBlob, 'recording.wav');

    // Show loading state
    pitchValueEl.textContent = '...';
    truthIndicatorEl.textContent = 'Analyzing...';

    try {
        const resp = await fetch('/analyze-audio', { method: 'POST', body: formData });
        const data = await resp.json();
        console.log('[Audio] Full analysis result:', data);

        if (data.status === 'error') {
            console.error('Audio analysis error:', data.error);
            pitchValueEl.textContent = 'Error';
            truthIndicatorEl.textContent = 'Error';
            return;
        }

        if (data.status === 'no_voice') {
            pitchValueEl.textContent = 'No voice';
            truthIndicatorEl.textContent = 'No voice detected';
            return;
        }

        // Update pitch
        if (typeof data.avg_pitch !== 'undefined') {
            pitchValueEl.textContent = Number(data.avg_pitch).toFixed(1);
        }

        // Update truth indicator
        if (data.truth_indicator) {
            const likelihood = typeof data.truth_likelihood !== 'undefined'
                ? ' (' + Number(data.truth_likelihood).toFixed(2) + ')'
                : '';
            truthIndicatorEl.textContent = data.truth_indicator + likelihood;

            // Color-code the truth indicator
            if (data.truth_indicator.includes('TRUTHFUL')) {
                truthIndicatorEl.style.color = '#2ed573';
            } else if (data.truth_indicator.includes('DECEPTION')) {
                truthIndicatorEl.style.color = '#ff4757';
            } else {
                truthIndicatorEl.style.color = '#ffa502';
            }
        }

        // Update stress level from audio (overrides video stress if audio was just recorded)
        if (data.stress_level) {
            const level = data.stress_level;
            stressLevelEl.textContent = level.toUpperCase() + ' (Voice)';
            stressLevelEl.className = `stress-indicator ${level}`;
            const pct = level === 'low' ? 20 : level === 'medium' ? 60 : 100;
            stressProgressEl.style.width = pct + '%';
        }

        // Show pitch variance as a sub-detail in the label
        if (typeof data.pitch_std !== 'undefined') {
            const pitchLabel = document.querySelector('.metric-card:nth-child(3) .label');
            if (pitchLabel) {
                pitchLabel.textContent = `Hz | variance: ±${Number(data.pitch_std).toFixed(1)}`;
            }
        }

        // Show silence ratio (hesitation indicator)
        if (typeof data.silence_ratio !== 'undefined') {
            const hesitation = Math.round(data.silence_ratio * 100);
            console.log(`[Audio] Hesitation/silence ratio: ${hesitation}%`);
            // Update truth card label with hesitation info
            const truthLabel = document.querySelector('.metric-card:nth-child(4) .label');
            if (truthLabel) {
                truthLabel.textContent = `likelihood (0-1) | hesitation: ${hesitation}%`;
            }
        }

    } catch (err) {
        console.error('Audio analysis fetch error:', err);
        pitchValueEl.textContent = 'Error';
    }

    audioChunks = [];
}

// Convert a recorded audio blob (ogg/webm) to WAV using Web Audio API
async function convertBlobToWav(blob) {
    const arrayBuffer = await blob.arrayBuffer();
    const ac = new (window.OfflineAudioContext || window.AudioContext)(1, 2, 44100);
    const decoded = await ac.decodeAudioData(arrayBuffer.slice(0));

    const numChannels = Math.min(2, decoded.numberOfChannels);
    const sampleRate = 44100;
    const length = decoded.length * numChannels;

    // Interleave channels
    let resultBuffer = new Float32Array(decoded.length * numChannels);
    if (numChannels === 1) {
        const ch0 = decoded.getChannelData(0);
        resultBuffer.set(ch0);
    } else {
        const ch0 = decoded.getChannelData(0);
        const ch1 = decoded.getChannelData(1);
        for (let i = 0, j = 0; i < decoded.length; i++, j += 2) {
            resultBuffer[j] = ch0[i];
            resultBuffer[j + 1] = ch1[i];
        }
    }

    // Encode WAV
    const wavBuffer = encodeWAV(resultBuffer, numChannels, sampleRate);
    return new Blob([wavBuffer], { type: 'audio/wav' });
}

function encodeWAV(samples, numChannels, sampleRate) {
    const buffer = new ArrayBuffer(44 + samples.length * 2);
    const view = new DataView(buffer);

    function writeString(view, offset, string) {
        for (let i = 0; i < string.length; i++) {
            view.setUint8(offset + i, string.charCodeAt(i));
        }
    }

    /* RIFF identifier */ writeString(view, 0, 'RIFF');
    /* file length */ view.setUint32(4, 36 + samples.length * 2, true);
    /* RIFF type */ writeString(view, 8, 'WAVE');
    /* format chunk identifier */ writeString(view, 12, 'fmt ');
    /* format chunk length */ view.setUint32(16, 16, true);
    /* sample format (raw) */ view.setUint16(20, 1, true);
    /* channel count */ view.setUint16(22, numChannels, true);
    /* sample rate */ view.setUint32(24, sampleRate, true);
    /* byte rate (sampleRate * blockAlign) */ view.setUint32(28, sampleRate * numChannels * 2, true);
    /* block align (channel count * bytesPerSample) */ view.setUint16(32, numChannels * 2, true);
    /* bits per sample */ view.setUint16(34, 16, true);
    /* data chunk identifier */ writeString(view, 36, 'data');
    /* data chunk length */ view.setUint32(40, samples.length * 2, true);

    // Write PCM samples
    let offset = 44;
    for (let i = 0; i < samples.length; i++, offset += 2) {
        const s = Math.max(-1, Math.min(1, samples[i]));
        view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
    }

    return view;
}