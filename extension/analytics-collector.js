/**
 * ExamGuard Pro - Advanced Analytics Collector
 * 
 * Client-side collection for:
 * - Behavioral Biometrics (keystroke + mouse dynamics)
 * - Gaze Tracking (using WebGazer.js or MediaPipe)
 * - Browser Forensics (VM, remote desktop, extensions)
 * - Audio Analysis (microphone monitoring)
 * 
 * 100% LOCAL PROCESSING - Data sent only to your own server.
 */

class AdvancedAnalyticsCollector {
    constructor(options = {}) {
        this.serverUrl = options.serverUrl || 'http://localhost:8000';
        this.studentId = options.studentId || 'unknown';
        this.sessionId = options.sessionId || this.generateSessionId();
        
        // Collection settings
        this.enabled = {
            biometrics: options.enableBiometrics !== false,
            gaze: options.enableGaze !== false,
            forensics: options.enableForensics !== false,
            audio: options.enableAudio !== false,
        };
        
        // Buffers for batching
        this.keystrokeBuffer = [];
        this.mouseBuffer = [];
        this.gazeBuffer = [];
        
        // Timing
        this.batchInterval = options.batchInterval || 5000; // 5 seconds
        this.lastSendTime = Date.now();
        
        // State
        this.isCollecting = false;
        this.audioContext = null;
        this.mediaStream = null;
        
        // Keystroke tracking state
        this.keyDownTimes = {};
        
        // Mouse tracking state
        this.lastMousePos = { x: 0, y: 0, time: 0 };
        
        // Bind methods
        this.handleKeyDown = this.handleKeyDown.bind(this);
        this.handleKeyUp = this.handleKeyUp.bind(this);
        this.handleMouseMove = this.handleMouseMove.bind(this);
        this.handleMouseClick = this.handleMouseClick.bind(this);
        this.handleScroll = this.handleScroll.bind(this);
    }
    
    generateSessionId() {
        return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }
    
    // =========================================================================
    // Lifecycle
    // =========================================================================
    
    async start() {
        if (this.isCollecting) return;
        
        console.log('[Analytics] Starting advanced collection...');
        this.isCollecting = true;
        
        // Start biometrics collection
        if (this.enabled.biometrics) {
            this.startBiometrics();
        }
        
        // Start forensics analysis
        if (this.enabled.forensics) {
            await this.collectForensics();
        }
        
        // Start audio monitoring
        if (this.enabled.audio) {
            await this.startAudioMonitoring();
        }
        
        // Start periodic sending
        this.sendInterval = setInterval(() => this.sendBatch(), this.batchInterval);
        
        console.log('[Analytics] Collection started');
    }
    
    stop() {
        if (!this.isCollecting) return;
        
        console.log('[Analytics] Stopping collection...');
        this.isCollecting = false;
        
        // Stop biometrics
        this.stopBiometrics();
        
        // Stop audio
        this.stopAudioMonitoring();
        
        // Stop sending
        if (this.sendInterval) {
            clearInterval(this.sendInterval);
        }
        
        // Send remaining data
        this.sendBatch();
        
        console.log('[Analytics] Collection stopped');
    }
    
    // =========================================================================
    // Biometrics Collection
    // =========================================================================
    
    startBiometrics() {
        document.addEventListener('keydown', this.handleKeyDown, true);
        document.addEventListener('keyup', this.handleKeyUp, true);
        document.addEventListener('mousemove', this.handleMouseMove, true);
        document.addEventListener('click', this.handleMouseClick, true);
        document.addEventListener('scroll', this.handleScroll, true);
        
        console.log('[Biometrics] Keystroke and mouse tracking started');
    }
    
    stopBiometrics() {
        document.removeEventListener('keydown', this.handleKeyDown, true);
        document.removeEventListener('keyup', this.handleKeyUp, true);
        document.removeEventListener('mousemove', this.handleMouseMove, true);
        document.removeEventListener('click', this.handleMouseClick, true);
        document.removeEventListener('scroll', this.handleScroll, true);
    }
    
    handleKeyDown(event) {
        const timestamp = performance.now();
        const key = event.key;
        
        // Store keydown time for dwell calculation
        if (!this.keyDownTimes[key]) {
            this.keyDownTimes[key] = timestamp;
            
            this.keystrokeBuffer.push({
                type: 'keystroke',
                key: this.normalizeKey(key),
                timestamp,
                event_type: 'keydown',
            });
        }
    }
    
    handleKeyUp(event) {
        const timestamp = performance.now();
        const key = event.key;
        
        // Calculate dwell time
        const downTime = this.keyDownTimes[key];
        if (downTime) {
            const dwellTime = timestamp - downTime;
            delete this.keyDownTimes[key];
            
            this.keystrokeBuffer.push({
                type: 'keystroke',
                key: this.normalizeKey(key),
                timestamp,
                event_type: 'keyup',
                dwell_time: dwellTime,
            });
        }
    }
    
    normalizeKey(key) {
        // Normalize key names for privacy (don't send actual typed characters)
        if (key.length === 1) {
            if (/[a-zA-Z]/.test(key)) return 'letter';
            if (/[0-9]/.test(key)) return 'digit';
            if (/\s/.test(key)) return 'space';
            return 'symbol';
        }
        return key.toLowerCase();
    }
    
    handleMouseMove(event) {
        const timestamp = performance.now();
        const x = event.clientX;
        const y = event.clientY;
        
        // Throttle mouse events (max 20 per second)
        if (timestamp - this.lastMousePos.time < 50) return;
        
        this.mouseBuffer.push({
            type: 'mouse',
            x,
            y,
            timestamp,
            event_type: 'move',
        });
        
        this.lastMousePos = { x, y, time: timestamp };
    }
    
    handleMouseClick(event) {
        const timestamp = performance.now();
        
        this.mouseBuffer.push({
            type: 'mouse',
            x: event.clientX,
            y: event.clientY,
            timestamp,
            event_type: 'click',
            button: event.button,
        });
    }
    
    handleScroll(event) {
        const timestamp = performance.now();
        
        this.mouseBuffer.push({
            type: 'scroll',
            timestamp,
            scroll_y: window.scrollY,
            delta: event.deltaY || 0,
        });
    }
    
    // =========================================================================
    // Gaze Tracking (Client-side estimation)
    // =========================================================================
    
    startGazeTracking() {
        // This requires WebGazer.js or similar library
        // For now, we'll use a simplified face position estimation
        
        if (typeof webgazer !== 'undefined') {
            webgazer.setGazeListener((data, timestamp) => {
                if (data) {
                    this.gazeBuffer.push({
                        x: (data.x / window.innerWidth) * 2 - 1,  // Normalize to -1 to 1
                        y: (data.y / window.innerHeight) * 2 - 1,
                        timestamp,
                        confidence: 0.8,
                    });
                }
            }).begin();
            
            console.log('[Gaze] WebGazer tracking started');
        } else {
            console.log('[Gaze] WebGazer not available - using simplified tracking');
        }
    }
    
    // =========================================================================
    // Browser Forensics
    // =========================================================================
    
    async collectForensics() {
        const forensicsData = {
            // Navigator info
            userAgent: navigator.userAgent,
            platform: navigator.platform,
            vendor: navigator.vendor,
            language: navigator.language,
            languages: Array.from(navigator.languages || []),
            
            // Hardware
            hardwareConcurrency: navigator.hardwareConcurrency || 0,
            deviceMemory: navigator.deviceMemory || 0,
            maxTouchPoints: navigator.maxTouchPoints || 0,
            
            // Screen
            screenWidth: screen.width,
            screenHeight: screen.height,
            availWidth: screen.availWidth,
            availHeight: screen.availHeight,
            colorDepth: screen.colorDepth,
            pixelRatio: window.devicePixelRatio || 1,
            screenCount: window.screen?.isExtended ? 2 : 1,
            
            // Timezone
            timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
            timezoneOffset: new Date().getTimezoneOffset(),
            
            // WebGL (VM detection)
            ...this.getWebGLInfo(),
            
            // Canvas fingerprint
            canvasFingerprint: this.getCanvasFingerprint(),
            
            // Audio fingerprint
            audioFingerprint: await this.getAudioFingerprint(),
            
            // Plugins
            plugins: this.getPlugins(),
            
            // Extensions (if detectable)
            extensions: await this.detectExtensions(),
            
            // Focus state
            windowFocused: document.hasFocus(),
            
            // Screen sharing detection
            displayMediaActive: this.isScreenSharing(),
            mediaRecorderActive: this.isRecording(),
        };
        
        // Send to server
        await this.sendForensics(forensicsData);
        
        return forensicsData;
    }
    
    getWebGLInfo() {
        try {
            const canvas = document.createElement('canvas');
            const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
            
            if (!gl) return { webglVendor: '', webglRenderer: '' };
            
            const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
            
            return {
                webglVendor: debugInfo ? gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL) : '',
                webglRenderer: debugInfo ? gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL) : '',
            };
        } catch (e) {
            return { webglVendor: '', webglRenderer: '' };
        }
    }
    
    getCanvasFingerprint() {
        try {
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            
            canvas.width = 200;
            canvas.height = 50;
            
            ctx.textBaseline = 'top';
            ctx.font = '14px Arial';
            ctx.fillStyle = '#f60';
            ctx.fillRect(125, 1, 62, 20);
            ctx.fillStyle = '#069';
            ctx.fillText('ExamGuard Pro', 2, 15);
            ctx.fillStyle = 'rgba(102, 204, 0, 0.7)';
            ctx.fillText('Canvas FP', 4, 35);
            
            return canvas.toDataURL().slice(-50);
        } catch (e) {
            return '';
        }
    }
    
    async getAudioFingerprint() {
        try {
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const analyser = audioContext.createAnalyser();
            const gain = audioContext.createGain();
            const processor = audioContext.createScriptProcessor(4096, 1, 1);
            
            gain.gain.value = 0; // Silent
            oscillator.type = 'triangle';
            oscillator.connect(analyser);
            analyser.connect(processor);
            processor.connect(gain);
            gain.connect(audioContext.destination);
            
            oscillator.start(0);
            
            return new Promise(resolve => {
                processor.onaudioprocess = (event) => {
                    const bins = new Float32Array(analyser.frequencyBinCount);
                    analyser.getFloatFrequencyData(bins);
                    
                    oscillator.disconnect();
                    processor.disconnect();
                    gain.disconnect();
                    audioContext.close();
                    
                    // Simple hash of first few bins
                    const hash = bins.slice(0, 10).reduce((a, b) => a + b, 0).toFixed(2);
                    resolve(hash);
                };
            });
        } catch (e) {
            return '';
        }
    }
    
    getPlugins() {
        try {
            return Array.from(navigator.plugins || []).map(p => p.name);
        } catch (e) {
            return [];
        }
    }
    
    async detectExtensions() {
        // This is limited by browser security
        // Real extension detection requires manifest inspection
        const extensions = [];
        
        // Try to detect common extensions by their injected content
        const knownPatterns = [
            { selector: '[data-grammarly-shadow-root]', name: 'Grammarly' },
            { selector: '#lastpass-icon-root', name: 'LastPass' },
            { selector: '.honey-gold-button', name: 'Honey' },
        ];
        
        for (const pattern of knownPatterns) {
            if (document.querySelector(pattern.selector)) {
                extensions.push({ name: pattern.name, detected: true });
            }
        }
        
        return extensions;
    }
    
    isScreenSharing() {
        // Check if getDisplayMedia is active
        // This is a rough detection
        return false; // Can't reliably detect from content script
    }
    
    isRecording() {
        return false; // Can't reliably detect
    }
    
    // =========================================================================
    // Audio Monitoring
    // =========================================================================
    
    async startAudioMonitoring() {
        try {
            this.mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
            this.audioContext = new AudioContext();
            
            const source = this.audioContext.createMediaStreamSource(this.mediaStream);
            const analyser = this.audioContext.createAnalyser();
            analyser.fftSize = 2048;
            
            source.connect(analyser);
            
            const bufferLength = analyser.frequencyBinCount;
            const dataArray = new Float32Array(bufferLength);
            
            // Monitor every 500ms
            this.audioMonitorInterval = setInterval(() => {
                analyser.getFloatTimeDomainData(dataArray);
                
                // Calculate RMS
                let sum = 0;
                for (let i = 0; i < bufferLength; i++) {
                    sum += dataArray[i] * dataArray[i];
                }
                const rms = Math.sqrt(sum / bufferLength);
                
                // If significant audio detected, send for analysis
                if (rms > 0.01) {
                    this.sendAudioSamples(Array.from(dataArray));
                }
            }, 500);
            
            console.log('[Audio] Monitoring started');
        } catch (e) {
            console.error('[Audio] Could not start monitoring:', e);
        }
    }
    
    stopAudioMonitoring() {
        if (this.audioMonitorInterval) {
            clearInterval(this.audioMonitorInterval);
        }
        
        if (this.mediaStream) {
            this.mediaStream.getTracks().forEach(track => track.stop());
        }
        
        if (this.audioContext) {
            this.audioContext.close();
        }
    }
    
    // =========================================================================
    // Data Sending
    // =========================================================================
    
    async sendBatch() {
        if (!this.isCollecting) return;
        
        const now = Date.now();
        
        // Send biometrics
        if (this.keystrokeBuffer.length > 0 || this.mouseBuffer.length > 0) {
            const events = [...this.keystrokeBuffer, ...this.mouseBuffer];
            this.keystrokeBuffer = [];
            this.mouseBuffer = [];
            
            await this.sendBiometrics(events);
        }
        
        // Send gaze data
        if (this.gazeBuffer.length > 0) {
            const gazePoints = [...this.gazeBuffer];
            this.gazeBuffer = [];
            
            await this.sendGaze(gazePoints);
        }
        
        this.lastSendTime = now;
    }
    
    async sendBiometrics(events) {
        try {
            await fetch(`${this.serverUrl}/api/analytics/biometrics/analyze`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    student_id: this.studentId,
                    session_id: this.sessionId,
                    events,
                }),
            });
        } catch (e) {
            console.error('[Analytics] Failed to send biometrics:', e);
        }
    }
    
    async sendGaze(gazePoints) {
        try {
            await fetch(`${this.serverUrl}/api/analytics/gaze/analyze`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    student_id: this.studentId,
                    session_id: this.sessionId,
                    gaze_points: gazePoints,
                }),
            });
        } catch (e) {
            console.error('[Analytics] Failed to send gaze:', e);
        }
    }
    
    async sendForensics(data) {
        try {
            const response = await fetch(`${this.serverUrl}/api/analytics/forensics/analyze`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    student_id: this.studentId,
                    session_id: this.sessionId,
                    data,
                }),
            });
            
            const result = await response.json();
            
            if (result.alerts && result.alerts.length > 0) {
                console.warn('[Forensics] Alerts:', result.alerts);
            }
            
            return result;
        } catch (e) {
            console.error('[Analytics] Failed to send forensics:', e);
        }
    }
    
    async sendAudioSamples(samples) {
        try {
            await fetch(`${this.serverUrl}/api/analytics/audio/analyze-samples`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    student_id: this.studentId,
                    samples,
                }),
            });
        } catch (e) {
            // Silent fail for audio - too frequent
        }
    }
    
    // =========================================================================
    // Combined Analysis
    // =========================================================================
    
    async getCombinedAnalysis() {
        try {
            const response = await fetch(
                `${this.serverUrl}/api/analytics/combined/${this.studentId}`
            );
            return await response.json();
        } catch (e) {
            console.error('[Analytics] Failed to get combined analysis:', e);
            return null;
        }
    }
}

// Export for use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AdvancedAnalyticsCollector;
}

// Auto-initialize if in extension context
if (typeof chrome !== 'undefined' && chrome.runtime) {
    window.AdvancedAnalyticsCollector = AdvancedAnalyticsCollector;
}
