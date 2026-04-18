/**
 * Safely send a message to background, catching "context invalidated" errors
 * and stopping active monitoring if the extension was reloaded.
 */
function safeSendMessage(message, callback) {
    try {
        if (!chrome.runtime || !chrome.runtime.id) {
            throw new Error('Context invalidated');
        }
        chrome.runtime.sendMessage(message, (response) => {
            if (chrome.runtime.lastError) {
                const err = chrome.runtime.lastError.message;
                if (err.includes('context invalidated')) {
                    stopAllMonitoring();
                }
            }
            if (callback) callback(response);
        });
        return true;
    } catch (e) {
        if (e.message.includes('context invalidated')) {
            stopAllMonitoring();
        }
        return false;
    }
}

function stopAllMonitoring() {
    behaviorMonitor.isMonitoring = false;
    console.log('🛡️ Monitoring stopped (Extension reloaded or session ended)');
}

// ==================== ADVANCED MONITORING MODULE ====================
class ExamMonitor {
    constructor() {
        this.lastKeyTime = Date.now();
        this.keyIntervals = [];
        this.mouseMovements = [];
        this.lastInputTime = Date.now();
        this.isMonitoring = false;
        this.typingBaselines = new Map(); // fieldId -> { chars, time }
        this.intervals = [];

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
            if (!this.isMonitoring) return;
            e.preventDefault();
            this.sendAlert('CONTEXT_MENU_BLOCKED', { message: 'Attempted right-click' });
        });

        // Block Drag & Drop
        document.addEventListener('drop', e => {
            if (!this.isMonitoring) return;
            e.preventDefault();
            this.sendAlert('DROP_BLOCKED', { message: 'Attempted drag-drop text' });
        });
        document.addEventListener('dragover', e => e.preventDefault());

        // Disable browser features on inputs
        const inputs = document.querySelectorAll('input, textarea');
        inputs.forEach(input => this.hardenInput(input));

        // Watch for new inputs
        const observer = new MutationObserver((mutations) => {
            if (!this.isMonitoring) return;
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
            if (!this.isMonitoring) return;
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
            if (!this.isMonitoring) return;
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
            if (!this.isMonitoring) return;
            this.lastInputTime = Date.now();
            const pos = { x: e.clientX, y: e.clientY, t: Date.now() };
            this.mouseMovements.push(pos);
            if (this.mouseMovements.length > 100) this.mouseMovements.shift();

            if (this.mouseMovements.length % 50 === 0) {
                this.calculateMouseEntropy();
            }
        });

        // Copy/Cut Detection
        document.addEventListener('copy', () => {
            if (!this.isMonitoring) return;
            this.sendAlert('COPY', { message: 'Text copied from exam page' });
        });
        document.addEventListener('cut', () => {
            if (!this.isMonitoring) return;
            this.sendAlert('CUT', { message: 'Text cut from exam page' });
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
        if (!this.isMonitoring || this.mouseMovements.length < 10) return;
        
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
        if (entropy > 0.8) {
            // Highly erratic movement
            // this.sendAlert('ERRATIC_MOUSE', { entropy: entropy.toFixed(2) });
        }
    }

    startDevToolsCheck() {
        const id = setInterval(() => {
            if (!this.isMonitoring) return;
            const start = performance.now();
            debugger;
            if (performance.now() - start > 100) {
                this.sendAlert('DEVTOOLS_DETECTED', { method: 'timing' });
            }
        }, 5000);
        this.intervals.push(id);

        window.addEventListener('resize', () => {
            if (!this.isMonitoring) return;
            const widthDiff = window.outerWidth - window.innerWidth;
            const heightDiff = window.outerHeight - window.innerHeight;
            if (widthDiff > 160 || heightDiff > 160) {
                this.sendAlert('DEVTOOLS_DETECTED', { method: 'resize', delta: widthDiff || heightDiff });
            }
        });
    }

    startHeartbeat() {
        const id = setInterval(() => {
            if (!this.isMonitoring) return;
            const idle = Date.now() - this.lastInputTime;
            if (idle > this.HEARTBEAT_INTERVAL) {
                this.sendAlert('INPUT_IDLE', { duration: Math.round(idle / 1000) });
            }
        }, 30000);
        this.intervals.push(id);
    }

    async checkVPN() {
        try {
            const pc = new RTCPeerConnection({ iceServers: [{ urls: 'stun:stun.l.google.com:19302' }] });
            pc.createDataChannel('');
            const offer = await pc.createOffer();
            await pc.setLocalDescription(offer);

            pc.onicecandidate = (e) => {
                if (!e.candidate || !this.isMonitoring) return;
                const ipMatch = e.candidate.candidate.match(/\d+\.\d+\.\d+\.\d+/);
                if (ipMatch) {
                    const localIp = ipMatch[0];
                    safeSendMessage({ 
                        type: 'NETWORK_INFO', 
                        data: { localIp, timestamp: Date.now() } 
                    });
                }
            };
        } catch (e) {}
    }

    sendAlert(type, data = {}) {
        if (!this.isMonitoring) return;
        safeSendMessage({
            type: 'BEHAVIOR_ALERT',
            data: {
                type,
                ...data,
                timestamp: Date.now(),
                url: window.location.href
            }
        });
    }

    stop() {
        this.isMonitoring = false;
        this.intervals.forEach(id => clearInterval(id));
        this.intervals = [];
    }
}

class ScreenCapture {
    startCapture() { return Promise.resolve(false); }
    stopCapture() {}
}

// ==================== INITIALIZATION ====================
const behaviorMonitor = new ExamMonitor();

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    try {
        if (message.type === 'START_SCREEN_CAPTURE' || message.type === 'EXAM_STARTED') {
            behaviorMonitor.start();
            startOverlayDetection();
            sendResponse({ success: true });
        } else if (message.type === 'STOP_SCREEN_CAPTURE' || message.type === 'EXAM_STOPPED') {
            stopAllMonitoring();
            sendResponse({ success: true });
        }
    } catch (e) {
        // Safe fail if context is dead
    }
    return true;
});

// ==================== OVERLAY / CLUELY DETECTION ====================
// Detects AI answer overlays injected into the DOM (Cluely, Interview Coder, etc.)

let overlayObserver = null;

function startOverlayDetection() {
    if (overlayObserver) return;

    // Scan existing DOM
    scanForOverlays();

    // Watch for new elements
    overlayObserver = new MutationObserver((mutations) => {
        for (const mutation of mutations) {
            for (const node of mutation.addedNodes) {
                if (node.nodeType === Node.ELEMENT_NODE) {
                    checkElementForOverlay(node);
                }
            }
        }
    });

    overlayObserver.observe(document.documentElement, {
        childList: true,
        subtree: true,
    });
}

function scanForOverlays() {
    // Check all elements with very high z-index (overlay pattern)
    const allElements = document.querySelectorAll('*');
    for (const el of allElements) {
        checkElementForOverlay(el);
    }
}

function checkElementForOverlay(el) {
    try {
        const style = window.getComputedStyle(el);
        const zIndex = parseInt(style.zIndex) || 0;
        const position = style.position;
        const pointerEvents = style.pointerEvents;

        // Cluely signature: fixed/absolute positioned, very high z-index, pointer-events: none
        const isSuspiciousOverlay = (
            zIndex > 9000 &&
            (position === 'fixed' || position === 'absolute') &&
            pointerEvents === 'none'
        );

        if (isSuspiciousOverlay) {
            const hasText = (el.textContent || '').trim().length > 20;
            if (hasText) {
                safeSendMessage({
                    type: 'BEHAVIOR_ALERT',
                    data: {
                        type: 'AI_OVERLAY_DETECTED',
                        message: 'Suspicious transparent overlay with text detected (possible Cluely/Interview Coder)',
                        zIndex,
                        textPreview: (el.textContent || '').slice(0, 100),
                        tagName: el.tagName,
                        className: el.className?.toString().slice(0, 100),
                        severity: 'CRITICAL',
                        timestamp: Date.now(),
                        url: window.location.href,
                    }
                });
            }
        }

        // Also check for iframes pointing to localhost:5180
        if (el.tagName === 'IFRAME') {
            const src = (el.src || '').toLowerCase();
            if (src.includes('localhost:5180') || src.includes('127.0.0.1:5180') || src.includes('cluely')) {
                safeSendMessage({
                    type: 'BEHAVIOR_ALERT',
                    data: {
                        type: 'CHEATING_IFRAME_DETECTED',
                        message: `Cheating tool iframe detected: ${src}`,
                        severity: 'CRITICAL',
                        timestamp: Date.now(),
                        url: window.location.href,
                    }
                });
            }
        }
    } catch (e) {
        // Silently fail for cross-origin elements
    }
}
