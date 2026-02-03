// Utility functions
export function randomId() {
    return Math.random().toString(36).substring(2, 11);
}

export function delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

export function sanitizeUrl(url) {
    try {
        const parsed = new URL(url);
        return `${parsed.protocol}//${parsed.hostname}${parsed.pathname}`;
    } catch {
        return url || 'unknown';
    }
}
