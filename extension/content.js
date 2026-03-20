// ==================== ADVANCED MONITORING MODULE ====================
class ExamMonitor {
    constructor() {
        this.lastKeyTime = Date.now();
        this.keyIntervals = [];
        this.mouseMovements = [];
        this.lastInputTime = Date.now();
        this.isMonitoring = false;
        this.typingBaselines = new Map(); // fieldId -> { chars, time }

        // Settings
        this.HEARTBEAT_INTERVAL = 30000; // 30s
        this.PASTE_THRESHOLD_MS = 100;    // 100ms
        this.PASTE_MIN_CHARS = 15;
    }

    start() {
        if (this.isMonitoring) return;
        this.isMonitoring = true;

        // 1. Lockdown Features
        this.applyLockdown();

        // 2. Event Listeners
        this.setupEventListeners();

        // 3. DevTools Detection
        this.startDevToolsCheck();

        // 4. Heartbeat (Inactivity detection)
        this.startHeartbeat();

        // 5. VPN Detection
        this.checkVPN();

        console.log('🛡️ Advanced monitoring active');
    }

    applyLockdown() {
        // Block Right-click
        document.addEventListener('contextmenu', e => {
            e.preventDefault();
            this.sendAlert('CONTEXT_MENU_BLOCKED', { message: 'Attempted right-click' });
        });

        // Block Drag & Drop
        document.addEventListener('drop', e => {
            e.preventDefault();
            this.sendAlert('DROP_BLOCKED', { message: 'Attempted drag-drop text' });
        });
        document.addEventListener('dragover', e => e.preventDefault());

        // Disable browser features on inputs
        const inputs = document.querySelectorAll('input, textarea');
        inputs.forEach(input => this.hardenInput(input));

        // Watch for new inputs
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                mutation.addedNodes.forEach((node) => {
                    if (node.tagName === 'INPUT' || node.tagName === 'TEXTAREA') {
                        this.hardenInput(node);
                    } else if (node.querySelectorAll) {
                        node.querySelectorAll('input, textarea').forEach(i => this.hardenInput(i));
                    }
                });
            });
        });
        observer.observe(document.body, { childList: true, subtree: true });
    }

    hardenInput(el) {
        el.setAttribute('autocomplete', 'off');
        el.setAttribute('autocorrect', 'off');
        el.setAttribute('autocapitalize', 'off');
        el.setAttribute('spellcheck', 'false');
    }

    setupEventListeners() {
        // Keystroke Dynamics & Paste Detection
        document.addEventListener('keydown', e => {
            const now = Date.now();
            const iki = now - this.lastKeyTime;
            this.lastKeyTime = now;
            this.lastInputTime = now;

            // Track inter-key intervals (passive fingerprinting)
            if (iki < 2000) this.keyIntervals.push(iki);
            if (this.keyIntervals.length > 50) this.keyIntervals.shift();

            // Detect keyboard paste (Ctrl+V / Cmd+V)
            if ((e.ctrlKey || e.metaKey) && e.key === 'v') {
                this.sendAlert('CLIPBOARD_PASTE', { method: 'keyboard' });
            }
        });

        // Detect high-velocity text injection (the "0ms paste")
        document.addEventListener('input', e => {
            if (e.inputType === 'insertFromPaste' || e.inputType === 'insertFromDrop') {
                this.sendAlert('PASTE_DETECTED', { type: e.inputType });
                return;
            }

            // Check velocity profiling
            if (e.target.tagName === 'TEXTAREA' || e.target.type === 'text') {
                this.profileVelocity(e.target);
            }
        });

        // Mouse Entropy & Erratic Movement
        document.addEventListener('mousemove', e => {
            this.lastInputTime = Date.now();
            const pos = { x: e.clientX, y: e.clientY, t: Date.now() };
            this.mouseMovements.push(pos);
            if (this.mouseMovements.length > 100) this.mouseMovements.shift();

            if (this.mouseMovements.length % 50 === 0) {
                this.calculateMouseEntropy();
            }
        });
    }

    profileVelocity(el) {
        const id = el.id || el.name || 'unnamed-input';
        const now = Date.now();
        const val = el.value;

        if (!this.typingBaselines.has(id)) {
            this.typingBaselines.set(id, { start: now, len: val.length });
            return;
        }

        const data = this.typingBaselines.get(id);
        const elapsed = (now - data.start) / 1000; // seconds
        const newChars = val.length - data.len;

        // If 20+ chars appear in < 0.2s, it's a programmatic injection/paste
        if (newChars > 15 && elapsed < 0.2) {
            this.sendAlert('VELOCITY_VIOLATION', {
                chars: newChars,
                time: elapsed,
                message: 'Instantaneous text injection detected'
            });
        }

        // Update baseline periodically
        if (elapsed > 5) {
            this.typingBaselines.set(id, { start: now, len: val.length });
        }
    }

    calculateMouseEntropy() {
        if (this.mouseMovements.length < 10) return;
        
        let erraticCount = 0;
        for (let i = 2; i < this.mouseMovements.length; i++) {
            const p1 = this.mouseMovements[i-2];
            const p2 = this.mouseMovements[i-1];
            const p3 = this.mouseMovements[i];
            
            // Calculate angle change (entropy of movement)
            const angle1 = Math.atan2(p2.y - p1.y, p2.x - p1.x);
            const angle2 = Math.atan2(p3.y - p2.y, p3.x - p2.x);
            const delta = Math.abs(angle1 - angle2);
            
            if (delta > 0.5) erraticCount++;
        }

        const entropy = erraticCount / this.mouseMovements.length;
        if (entropy < 0.05) { 
            // Too robotic/straight/still
            // Only flag if monitoring is long enough
        }
    }

    startDevToolsCheck() {
        // Method 1: Debugger timing
        setInterval(() => {
            const start = performance.now();
            debugger;
            if (performance.now() - start > 100) {
                this.sendAlert('DEVTOOLS_DETECTED', { method: 'timing' });
            }
        }, 3000);

        // Method 2: Size delta (docked tools)
        window.addEventListener('resize', () => {
            const widthDiff = window.outerWidth - window.innerWidth;
            const heightDiff = window.outerHeight - window.innerHeight;
            if (widthDiff > 160 || heightDiff > 160) {
                this.sendAlert('DEVTOOLS_DETECTED', { method: 'resize', delta: widthDiff || heightDiff });
            }
        });
    }

    startHeartbeat() {
        setInterval(() => {
            const idle = Date.now() - this.lastInputTime;
            if (idle > this.HEARTBEAT_INTERVAL) {
                this.sendAlert('INPUT_IDLE', { duration: Math.round(idle / 1000) });
            }
        }, 10000);
    }

    async checkVPN() {
        try {
            const pc = new RTCPeerConnection({ iceServers: [{ urls: 'stun:stun.l.google.com:19302' }] });
            pc.createDataChannel('');
            const offer = await pc.createOffer();
            await pc.setLocalDescription(offer);

            pc.onicecandidate = (e) => {
                if (!e.candidate) return;
                const ipMatch = e.candidate.candidate.match(/\d+\.\d+\.\d+\.\d+/);
                if (ipMatch) {
                    const localIp = ipMatch[0];
                    chrome.runtime.sendMessage({ 
                        type: 'NETWORK_INFO', 
                        data: { localIp, timestamp: Date.now() } 
                    });
                }
            };
        } catch (e) {
            console.warn('WebRTC IP leak check blocked');
        }
    }

    sendAlert(type, data) {
        chrome.runtime.sendMessage({
            type: 'BEHAVIOR_ALERT',
            data: {
                type,
                ...data,
                timestamp: Date.now(),
                url: window.location.href
            }
        });
    }
}

// ==================== SCREEN CAPTURE MODULE ====================
class ScreenCapture {
    constructor() {
        this.stream = null;
        this.captureInterval = null;
        this.isCapturing = false;
    }

    async startCapture(intervalMs = 5000) {
        try {
            this.stream = await navigator.mediaDevices.getDisplayMedia({
                video: { mediaSource: 'screen' }
            });

            this.isCapturing = true;
            this.captureInterval = setInterval(() => this.captureFrame(), intervalMs);
            console.log('Screen capture started');
            return true;
        } catch (error) {
            console.error('Screen capture failed:', error);
            return false;
        }
    }

    async captureFrame() {
        if (!this.stream || !this.isCapturing) return null;

        try {
            const track = this.stream.getVideoTracks()[0];
            if (!track || track.readyState !== 'live') return null;

            let dataUrl;

            try {
                if ('ImageCapture' in window) {
                    const imageCapture = new ImageCapture(track);
                    const bitmap = await imageCapture.grabFrame();

                    const canvas = document.createElement('canvas');
                    canvas.width = bitmap.width;
                    canvas.height = bitmap.height;
                    const ctx = canvas.getContext('2d');
                    ctx.drawImage(bitmap, 0, 0);
                    bitmap.close();

                    dataUrl = canvas.toDataURL('image/jpeg', 0.7);
                } else {
                    throw new Error('ImageCapture not available');
                }
            } catch (icError) {
                const video = document.createElement('video');
                video.srcObject = this.stream;
                video.muted = true;
                video.playsInline = true;
                await new Promise((resolve) => {
                    video.onloadedmetadata = () => { video.play().then(resolve).catch(resolve); };
                    setTimeout(resolve, 3000);
                });

                const canvas = document.createElement('canvas');
                canvas.width = video.videoWidth || 1280;
                canvas.height = video.videoHeight || 720;
                const ctx = canvas.getContext('2d');
                ctx.drawImage(video, 0, 0);
                video.srcObject = null;

                dataUrl = canvas.toDataURL('image/jpeg', 0.7);
            }

            chrome.runtime.sendMessage({
                type: 'SCREEN_CAPTURE',
                data: { image: dataUrl, timestamp: Date.now() }
            }, (response) => {
                if (chrome.runtime.lastError) {
                    console.warn('Screen capture send error:', chrome.runtime.lastError.message);
                }
            });

            return dataUrl;
        } catch (error) {
            console.error('Frame capture error:', error);
            return null;
        }
    }

    stopCapture() {
        if (this.captureInterval) {
            clearInterval(this.captureInterval);
            this.captureInterval = null;
        }
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
        this.isCapturing = false;
        console.log('Screen capture stopped');
    }
}

// ==================== DOM CAPTURE MODULE (html2canvas) ====================
class DOMCapture {
    constructor() {
        this.captureInterval = null;
        this.isCapturing = false;
        this.LAST_CAPTURE_HASH = '';
    }

    async start(intervalMs = 15000) { // Every 15s for DOM capture (lighter than video)
        if (this.isCapturing) return;
        this.isCapturing = true;
        
        console.log('🖼️ DOM-based monitoring started');
        this.captureInterval = setInterval(() => this.capture(), intervalMs);
        this.capture(); // Initial capture
    }

    stop() {
        if (this.captureInterval) {
            clearInterval(this.captureInterval);
            this.captureInterval = null;
        }
        this.isCapturing = false;
    }

    async capture() {
        if (!this.isCapturing || document.hidden) return;

        try {
            // Focus on the main content area (usually body or a specific container)
            const targetElement = document.body;
            
            const canvas = await html2canvas(targetElement, {
                scale: 0.5, // Reduced scale for performance
                logging: false,
                useCORS: true,
                allowTaint: true,
                // Only capture visible viewport for "what exactly is being watched"
                width: window.innerWidth,
                height: window.innerHeight,
                x: window.scrollX,
                y: window.scrollY
            });

            const dataUrl = canvas.toDataURL('image/jpeg', 0.5);
            
            // Send capture to background
            chrome.runtime.sendMessage({
                type: 'DOM_CONTENT_CAPTURE',
                data: {
                    image: dataUrl,
                    url: window.location.href,
                    title: document.title,
                    timestamp: Date.now(),
                    scrollPos: { x: window.scrollX, y: window.scrollY }
                }
            });

        } catch (error) {
            console.warn('DOM capture failed:', error.message);
        }
    }
}

// ==================== INITIALIZATION ====================
const screenCapture = new ScreenCapture();
const domCapture = new DOMCapture();
const behaviorMonitor = new ExamMonitor();

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === 'START_SCREEN_CAPTURE' || message.type === 'EXAM_STARTED') {
        screenCapture.startCapture(message.interval || 5000).then(sendResponse);
        domCapture.start(20000); // Higher interval for DOM (save resources)
        behaviorMonitor.start();
        return true;
    }
    if (message.type === 'STOP_SCREEN_CAPTURE' || message.type === 'EXAM_STOPPED') {
        screenCapture.stopCapture();
        domCapture.stop();
        behaviorMonitor.isMonitoring = false;
        sendResponse({ success: true });
    }
});
