// Utility functions for ExamGuard Pro extension
// Note: Content scripts don't support ES6 modules, so we use global functions

const ExamGuardUtils = {
    randomId() {
        return Math.random().toString(36).substring(2, 11);
    },

    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    },

    sanitizeUrl(url) {
        try {
            const parsed = new URL(url);
            return `${parsed.protocol}//${parsed.hostname}${parsed.pathname}`;
        } catch {
            return url || 'unknown';
        }
    }
};

// Also expose as global functions for backward compatibility
function randomId() {
    return ExamGuardUtils.randomId();
}

function delay(ms) {
    return ExamGuardUtils.delay(ms);
}

function sanitizeUrl(url) {
    return ExamGuardUtils.sanitizeUrl(url);
}
