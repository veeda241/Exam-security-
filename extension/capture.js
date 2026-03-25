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
            screenshotIntervalMs: 2500,
            webcamIntervalMs: 2000,
            imageQuality: 0.7,
            maxWidth: 1280,
            maxHeight: 720,
            webcamWidth: 640,
            webcamHeight: 480,
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

            // Start interval
            this.screenshotInterval = setInterval(() => {
                this.takeScreenshot();
            }, this.config.screenshotIntervalMs);

            // First capture immediately
            this.takeScreenshot();

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

    async takeScreenshot() {
        if (!this.screenStream || !this.screenStream.active) {
            this.errorCount.screen++;
            if (this.errorCount.screen >= this.config.maxErrors) {
                console.warn('⚠️ Too many screen capture errors, stopping');
                this.stopScreenCapture();
            }
            return;
        }

        try {
            const videoTrack = this.screenStream.getVideoTracks()[0];
            if (!videoTrack || videoTrack.readyState !== 'live') return;

            // Use ImageCapture API if available for better performance
            if ('ImageCapture' in window) {
                await this.captureWithImageCapture(videoTrack, 'screen');
            } else {
                await this.captureWithCanvas(this.screenStream, 'screen');
            }

            this.captureCount.screen++;
            this.errorCount.screen = 0;
        } catch (error) {
            console.error('Screenshot error:', error?.message || error || 'Unknown');
            this.errorCount.screen++;
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

            // Start interval
            this.webcamInterval = setInterval(() => {
                this.captureWebcamFrame();
            }, this.config.webcamIntervalMs);

            // First capture immediately
            this.captureWebcamFrame();

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

    async captureWebcamFrame() {
        if (!this.webcamStream || !this.webcamStream.active) {
            this.errorCount.webcam++;
            if (this.errorCount.webcam >= this.config.maxErrors) {
                console.warn('⚠️ Too many webcam errors, stopping');
                this.stopWebcamCapture();
            }
            return;
        }

        try {
            const videoTrack = this.webcamStream.getVideoTracks()[0];
            if (!videoTrack || videoTrack.readyState !== 'live') return;

            if ('ImageCapture' in window) {
                await this.captureWithImageCapture(videoTrack, 'webcam');
            } else {
                await this.captureWithCanvas(this.webcamStream, 'webcam');
            }

            this.captureCount.webcam++;
            this.errorCount.webcam = 0;
        } catch (error) {
            console.error('Webcam capture error:', error?.message || error || 'Unknown');
            this.errorCount.webcam++;
        }
    }

    // ==================== CAPTURE METHODS ====================

    async captureWithImageCapture(videoTrack, type) {
        try {
            const imageCapture = new ImageCapture(videoTrack);
            // Use grabFrame (always supported) instead of takePhoto
            // takePhoto calls setPhotoOptions which fails on screen capture tracks
            const bitmap = await imageCapture.grabFrame();

            let width = bitmap.width;
            let height = bitmap.height;
            const maxW = type === 'screen' ? this.config.maxWidth : this.config.webcamWidth;
            const maxH = type === 'screen' ? this.config.maxHeight : this.config.webcamHeight;

            if (width > maxW) {
                const ratio = maxW / width;
                width = maxW;
                height = Math.round(height * ratio);
            }
            if (height > maxH) {
                const ratio = maxH / height;
                height = maxH;
                width = Math.round(width * ratio);
            }

            const canvas = document.createElement('canvas');
            canvas.width = width;
            canvas.height = height;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(bitmap, 0, 0, width, height);
            bitmap.close();

            const dataUrl = canvas.toDataURL('image/jpeg', this.config.imageQuality);
            this.sendCapture(type, dataUrl);
        } catch (err) {
            // Fallback to canvas method if ImageCapture fails
            console.warn(`ImageCapture failed for ${type}, falling back to canvas:`, err?.message || err);
            const stream = type === 'screen' ? this.screenStream : this.webcamStream;
            if (stream) {
                await this.captureWithCanvas(stream, type);
            }
        }
    }

    async captureWithCanvas(stream, type) {
        const video = document.createElement('video');
        video.srcObject = stream;
        video.muted = true;
        video.playsInline = true;

        await new Promise((resolve, reject) => {
            video.onloadedmetadata = () => {
                video.play().then(resolve).catch(err => reject(err || new Error('Video play failed')));
            };
            video.onerror = (e) => reject(new Error('Video stream error'));
            setTimeout(() => reject(new Error('Video load timeout')), 5000);
        });

        // Calculate dimensions
        let width = video.videoWidth;
        let height = video.videoHeight;

        if (type === 'screen') {
            if (width > this.config.maxWidth) {
                const ratio = this.config.maxWidth / width;
                width = this.config.maxWidth;
                height = Math.round(height * ratio);
            }
            if (height > this.config.maxHeight) {
                const ratio = this.config.maxHeight / height;
                height = this.config.maxHeight;
                width = Math.round(width * ratio);
            }
        }

        const canvas = document.createElement('canvas');
        canvas.width = width;
        canvas.height = height;

        const ctx = canvas.getContext('2d');
        ctx.drawImage(video, 0, 0, width, height);

        const dataUrl = canvas.toDataURL('image/jpeg', this.config.imageQuality);

        video.srcObject = null;
        this.sendCapture(type, dataUrl);
    }

    sendCapture(type, dataUrl) {
        const messageType = type === 'screen' ? 'UPLOAD_SCREENSHOT' : 'UPLOAD_WEBCAM';

        // Use callback-style sendMessage to avoid channel-closed errors
        try {
            chrome.runtime.sendMessage({
                type: messageType,
                data: dataUrl,
            }, (response) => {
                if (chrome.runtime.lastError) {
                    // This is expected if the port closes before the response arrives (slow upload)
                    // We only log it as info if it's the specific "message port closed" error
                    const errMsg = chrome.runtime.lastError.message || '';
                    if (errMsg.includes('message port closed')) {
                        console.info(`${type} port closed (upload continues)`);
                    } else {
                        console.warn(`${type} upload channel:`, errMsg);
                    }
                }
            });
        } catch (err) {
            console.warn(`${type} upload error:`, err?.message || 'Context invalidated');
        }

        console.log(`📷 ${type === 'screen' ? 'Screenshot' : 'Webcam frame'} #${this.captureCount[type] + 1}`);
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

    // ==================== UNIFIED CONTROLS ====================

    async startAll() {
        this.isCapturing = true;
        this.captureCount = { screen: 0, webcam: 0 };
        this.errorCount = { screen: 0, webcam: 0 };

        const [screenResult, webcamResult] = await Promise.allSettled([
            this.startScreenCapture(),
            this.startWebcamCapture(),
        ]);

        return {
            screen: screenResult.status === 'fulfilled' ? screenResult.value : { success: false, error: screenResult.reason },
            webcam: webcamResult.status === 'fulfilled' ? webcamResult.value : { success: false, error: webcamResult.reason },
        };
    }

    stopAll() {
        this.isCapturing = false;
        this.stopScreenCapture();
        this.stopWebcamCapture();
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
}

// Export
window.ExamCapture = ExamCapture;
