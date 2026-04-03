/**
 * ExamGuard Pro - Capture Module v2.0
 * Enhanced screen and webcam capture with adaptive quality and error recovery
 */

class ExamCapture {
    constructor() {
        this.screenStream = null;
        this.webcamStream = null;
        this.screenshotInterval = null;
        this.webcamInterval = null;
        this.isCapturing = false;
        this.captureCount = { screen: 0, webcam: 0 };
        this.errorCount = { screen: 0, webcam: 0 };

        // Adaptive configuration
        this.config = {
            maxWidth: 854,
            maxHeight: 480,
            webcamWidth: 320,
            webcamHeight: 240,
            maxErrors: 5,
        };
    }

    // ==================== SCREEN CAPTURE ====================

    async startScreenCapture() {
        try {
            // Stop any existing capture first
            this.stopScreenCapture();

            this.screenStream = await navigator.mediaDevices.getDisplayMedia({
                video: {
                    cursor: 'always',
                    displaySurface: 'monitor',
                    width: { ideal: this.config.maxWidth },
                    height: { ideal: this.config.maxHeight },
                },
                audio: false,
            });

            console.log('📸 Screen capture initialized');

            // Reset error count on success
            this.errorCount.screen = 0;


            // Handle stream end
            this.screenStream.getVideoTracks()[0].onended = () => {
                console.log('📸 Screen share stopped by user');
                this.stopScreenCapture();
                this.notifyBackground('SCREEN_SHARE_STOPPED', { reason: 'User stopped sharing' });
            };

            return { success: true };
        } catch (error) {
            console.error('❌ Screen capture failed:', error?.name || 'Error', error?.message || error || 'Unknown');
            return {
                success: false,
                error: error?.message || 'Permission denied',
                errorType: error?.name || 'Error'
            };
        }
    }



    // ==================== WEBCAM CAPTURE ====================

    async startWebcamCapture() {
        try {
            // Stop any existing capture first
            this.stopWebcamCapture();

            this.webcamStream = await navigator.mediaDevices.getUserMedia({
                video: {
                    width: { ideal: this.config.webcamWidth },
                    height: { ideal: this.config.webcamHeight },
                    facingMode: 'user',
                    frameRate: { ideal: 15 },
                },
                audio: false,
            });

            console.log('📹 Webcam capture initialized');
            this.errorCount.webcam = 0;


            // Handle track end
            this.webcamStream.getVideoTracks()[0].onended = () => {
                console.log('📹 Webcam stopped');
                this.stopWebcamCapture();
                this.notifyBackground('WEBCAM_STOPPED', { reason: 'Camera disconnected' });
            };

            return { success: true };
        } catch (error) {
            console.error('❌ Webcam failed:', error?.name || 'Error', error?.message || error || 'Unknown');
            return {
                success: false,
                error: error?.message || 'Permission denied',
                errorType: error?.name || 'Error'
            };
        }
    }




    // ==================== STOP METHODS ====================

    stopScreenCapture() {
        if (this.screenshotInterval) {
            clearInterval(this.screenshotInterval);
            this.screenshotInterval = null;
        }

        if (this.screenStream) {
            this.screenStream.getTracks().forEach(track => track.stop());
            this.screenStream = null;
        }

        console.log('📸 Screen capture stopped');
    }

    stopWebcamCapture() {
        if (this.webcamInterval) {
            clearInterval(this.webcamInterval);
            this.webcamInterval = null;
        }

        if (this.webcamStream) {
            this.webcamStream.getTracks().forEach(track => track.stop());
            this.webcamStream = null;
        }

        console.log('📹 Webcam capture stopped');
    }

    /**
     * Capture a single frame from the active webcam stream
     * @returns {string|null} Base64 JPEG data URL
     */
    captureWebcamFrame() {
        if (!this.webcamStream || !this.webcamStream.active) return null;

        try {
            // Create a temporary video element to play the stream if not already playing
            if (!this._captureVideo) {
                this._captureVideo = document.createElement('video');
                this._captureVideo.srcObject = this.webcamStream;
                this._captureVideo.muted = true;
                this._captureVideo.play();
            }

            const canvas = document.createElement('canvas');
            canvas.width = this.config.webcamWidth;
            canvas.height = this.config.webcamHeight;
            const ctx = canvas.getContext('2d');
            
            // Draw current video frame to canvas
            ctx.drawImage(this._captureVideo, 0, 0, canvas.width, canvas.height);
            
            // Return as compressed JPEG
            return canvas.toDataURL('image/jpeg', 0.6);
        } catch (error) {
            console.warn('Webcam frame capture failed:', error);
            return null;
        }
    }

    // ==================== UNIFIED CONTROLS ====================

    async startAll() {
        this.isCapturing = true;
        this.captureCount = { screen: 0, webcam: 0 };
        this.errorCount = { screen: 0, webcam: 0 };

        const [screenResult, webcamResult] = await Promise.allSettled([
            this.startScreenCapture(),
            this.startWebcamCapture(),
        ]);

        // Kick off WebRTC P2P signaling using the gathered streams
        this.initWebRTC();

        return {
            screen: screenResult.status === 'fulfilled' ? screenResult.value : { success: false, error: screenResult.reason },
            webcam: webcamResult.status === 'fulfilled' ? webcamResult.value : { success: false, error: webcamResult.reason },
        };
    }

    stopAll() {
        this.isCapturing = false;
        if (this.pc) {
            this.pc.close();
            this.pc = null;
        }
        this.stopMediaRecorder();
        this.stopScreenCapture();
        this.stopWebcamCapture();
    }

    // ==================== LIVE STREAMING (MEDIA RECORDER) ====================

    startMediaRecorder(intervalMs = 1000) {
        if (!this.screenStream || !this.screenStream.active) {
            console.warn('❌ Cannot start MediaRecorder: Screen stream inactive');
            return;
        }

        try {
            // Options for high performance / low latency
            const options = {
                mimeType: 'video/webm; codecs=vp8',
                videoBitsPerSecond: 800000 // 800 Kbps (Balance quality/bandwidth)
            };

            this.mediaRecorder = new MediaRecorder(this.screenStream, options);

            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0 && this.isCapturing) {
                    // Send binary chunk to background script
                    // Note: Chrome extensions can send Blobs/ArrayBuffers via sendMessage
                    chrome.runtime.sendMessage({
                        type: 'STREAM_CHUNK',
                        data: event.data
                    }).catch(() => { });
                }
            };

            this.mediaRecorder.start(intervalMs);
            console.log('🎥 Live streaming started (MediaRecorder)');
        } catch (e) {
            console.error('🎥 MediaRecorder start failed:', e);
        }
    }

    stopMediaRecorder() {
        if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
            this.mediaRecorder.stop();
            this.mediaRecorder = null;
        }
        console.log('🎥 Live streaming stopped');
    }

    getStatus() {
        return {
            isCapturing: this.isCapturing,
            hasScreen: !!this.screenStream && this.screenStream.active,
            hasWebcam: !!this.webcamStream && this.webcamStream.active,
            captureCount: this.captureCount,
            errorCount: this.errorCount,
        };
    }

    // ==================== UTILITIES ====================

    blobToDataUrl(blob) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(reader.result);
            reader.onerror = reject;
            reader.readAsDataURL(blob);
        });
    }

    notifyBackground(eventType, data) {
        chrome.runtime.sendMessage({
            type: 'LOG_EVENT',
            event: {
                type: eventType,
                timestamp: Date.now(),
                data: data,
            }
        }).catch(() => { });
    }

    // ==================== WEBRTC INJECTION ====================
    initWebRTC() {
        if (this.pc) {
            this.pc.close();
        }

        this.pc = new RTCPeerConnection({
            iceServers: [{ urls: 'stun:stun.l.google.com:19302' }]
        });

        // Add 2 generic video tracks: first webcam, second screen
        if (this.webcamStream && this.webcamStream.getVideoTracks()[0]) {
            this.webcamStream.getVideoTracks()[0].enabled = true;
            this.pc.addTrack(this.webcamStream.getVideoTracks()[0], this.webcamStream);
        }
        if (this.screenStream && this.screenStream.getVideoTracks()[0]) {
            this.screenStream.getVideoTracks()[0].enabled = true;
            this.pc.addTrack(this.screenStream.getVideoTracks()[0], this.screenStream);
        }

        this.pc.onicecandidate = (event) => {
             if (event.candidate) {
                 chrome.runtime.sendMessage({
                     type: 'WEBRTC_SIGNAL_OUT',
                     payload: { candidate: event.candidate }
                 });
             }
        };

        // Student is the offerer. They open P2P with their ready streams
        this.pc.createOffer().then(offer => {
            return this.pc.setLocalDescription(offer);
        }).then(() => {
            chrome.runtime.sendMessage({
                type: 'WEBRTC_SIGNAL_OUT',
                payload: { sdp: this.pc.localDescription }
            });
        }).catch(err => console.error("WebRTC Offer Error:", err));
    }

    async handleWebRTCSignal(payload) {
        console.log('[WebRTC] Received signal:', payload);
        if (!this.pc) {
            console.error('[WebRTC] No peer connection available');
            return;
        }
        try {
            if (payload.sdp) {
                console.log('[WebRTC] Setting remote description:', payload.sdp.type);
                await this.pc.setRemoteDescription(new RTCSessionDescription(payload.sdp));
                console.log('[WebRTC] Remote description set successfully');
            } else if (payload.candidate) {
                console.log('[WebRTC] Adding ICE candidate');
                await this.pc.addIceCandidate(new RTCIceCandidate(payload.candidate));
            } else {
                console.log('[WebRTC] Unknown signal type:', payload);
            }
        } catch (e) {
            console.error("[WebRTC] Signaling Error", e);
        }
    }
}

// Global Message Listener for WebRTC from Background
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === 'WEBRTC_SIGNAL_IN' && window.ExamCaptureInstance) {
        window.ExamCaptureInstance.handleWebRTCSignal(message.payload);
        sendResponse({ success: true });
        return true;
    }
    
    if (message.type === 'REQUEST_WEBRTC_OFFER' && window.ExamCaptureInstance) {
        console.log("📡 Dashboard requested WEBRTC offer, re-initializing...");
        window.ExamCaptureInstance.initWebRTC();
        sendResponse({ success: true });
        return true;
    }
});

// Export
window.ExamCapture = ExamCapture;
