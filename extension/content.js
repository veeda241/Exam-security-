// Screen Capture Module
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

            // Try ImageCapture.grabFrame first, fall back to canvas on failure
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
                // Fallback: draw stream to video element then to canvas
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

            // Send to background script using callback style to avoid channel-closed errors
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

// Initialize and listen for messages
const screenCapture = new ScreenCapture();

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === 'START_SCREEN_CAPTURE') {
        screenCapture.startCapture(message.interval || 5000).then(sendResponse);
        return true;
    }
    if (message.type === 'STOP_SCREEN_CAPTURE') {
        screenCapture.stopCapture();
        sendResponse({ success: true });
    }
});
