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
            const imageCapture = new ImageCapture(track);
            const bitmap = await imageCapture.grabFrame();

            const canvas = document.createElement('canvas');
            canvas.width = bitmap.width;
            canvas.height = bitmap.height;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(bitmap, 0, 0);

            const dataUrl = canvas.toDataURL('image/jpeg', 0.7);

            // Send to background script
            chrome.runtime.sendMessage({
                type: 'SCREEN_CAPTURE',
                data: { image: dataUrl, timestamp: Date.now() }
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
