// Event Logger Module - Logs typing, clicks, and other user interactions
class EventLogger {
    constructor() {
        this.events = [];
        this.isLogging = false;
        this.typingTimeout = null;
        this.lastTypingTime = 0;
    }

    startLogging() {
        if (this.isLogging) return;

        this.isLogging = true;

        // Track clicks
        document.addEventListener('click', this.handleClick.bind(this));

        // Track typing
        document.addEventListener('keydown', this.handleKeydown.bind(this));

        // Track copy/paste
        document.addEventListener('copy', this.handleCopy.bind(this));
        document.addEventListener('paste', this.handlePaste.bind(this));

        // Track focus changes
        document.addEventListener('visibilitychange', this.handleVisibility.bind(this));

        console.log('Event logging started');
    }

    stopLogging() {
        this.isLogging = false;
        document.removeEventListener('click', this.handleClick);
        document.removeEventListener('keydown', this.handleKeydown);
        document.removeEventListener('copy', this.handleCopy);
        document.removeEventListener('paste', this.handlePaste);
        document.removeEventListener('visibilitychange', this.handleVisibility);
        console.log('Event logging stopped');
    }

    handleClick(event) {
        this.logEvent('CLICK', {
            target: event.target.tagName,
            x: event.clientX,
            y: event.clientY
        });
    }

    handleKeydown(event) {
        const now = Date.now();
        // Debounce typing events
        if (now - this.lastTypingTime > 1000) {
            this.logEvent('TYPING', { key: event.key.length === 1 ? '[key]' : event.key });
            this.lastTypingTime = now;
        }
    }

    handleCopy(event) {
        const text = window.getSelection().toString();
        this.logEvent('COPY', { textLength: text.length, preview: text.substring(0, 50) });
    }

    handlePaste(event) {
        const text = event.clipboardData?.getData('text') || '';
        this.logEvent('PASTE', { textLength: text.length, preview: text.substring(0, 50) });

        // Send clipboard text for similarity analysis
        chrome.runtime.sendMessage({
            type: 'CLIPBOARD_TEXT',
            data: { text, timestamp: Date.now() }
        });
    }

    handleVisibility() {
        this.logEvent('VISIBILITY_CHANGE', { hidden: document.hidden });
    }

    logEvent(type, data) {
        const event = {
            type,
            data,
            timestamp: Date.now(),
            url: window.location.href
        };

        this.events.push(event);

        // Send to background script
        chrome.runtime.sendMessage({ type: 'LOG_EVENT', event });

        // Keep only last 100 events in memory
        if (this.events.length > 100) {
            this.events.shift();
        }
    }
}

// Initialize
const eventLogger = new EventLogger();

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === 'START_EVENT_LOGGING') {
        eventLogger.startLogging();
        sendResponse({ success: true });
    }
    if (message.type === 'STOP_EVENT_LOGGING') {
        eventLogger.stopLogging();
        sendResponse({ success: true });
    }
});
