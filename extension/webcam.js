// Webcam Feed Module
class WebcamCapture {
    constructor() {
        this.stream = null;
        this.captureInterval = null;
        this.isCapturing = false;
        this.video = null;
    }

    async startCapture(intervalMs = 3000) {
        try {
            this.stream = await navigator.mediaDevices.getUserMedia({
                video: { width: 640, height: 480, facingMode: 'user' }
            });

            this.video = document.createElement('video');
            this.video.srcObject = this.stream;
            this.video.play();

            this.isCapturing = true;
            this.captureInterval = setInterval(() => this.captureFrame(), intervalMs);
            console.log('Webcam capture started');
            return true;
        } catch (error) {
            console.error('Webcam access failed:', error);
            return false;
        }
    }

    captureFrame() {
        if (!this.video || !this.isCapturing) return null;

        try {
            const canvas = document.createElement('canvas');
            canvas.width = this.video.videoWidth || 640;
            canvas.height = this.video.videoHeight || 480;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(this.video, 0, 0);

            const dataUrl = canvas.toDataURL('image/jpeg', 0.6);

            // Send to background script
            chrome.runtime.sendMessage({
                type: 'WEBCAM_CAPTURE',
                data: { image: dataUrl, timestamp: Date.now() }
            });

            return dataUrl;
        } catch (error) {
            console.error('Webcam frame error:', error);
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
        if (this.video) {
            this.video.srcObject = null;
            this.video = null;
        }
        this.isCapturing = false;
        console.log('Webcam capture stopped');
    }
}

// Initialize and listen for messages
const webcamCapture = new WebcamCapture();

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === 'START_WEBCAM_CAPTURE') {
        webcamCapture.startCapture(message.interval || 3000).then(sendResponse);
        return true;
    }
    if (message.type === 'STOP_WEBCAM_CAPTURE') {
        webcamCapture.stopCapture();
        sendResponse({ success: true });
    }
});
