/**
 * ExamGuard Pro V2 — versioned extension↔backend protocol.
 * Loaded via importScripts in the service worker.
 */
const PROTOCOL_VERSION = 1;

const EVENT_TYPES = {
  TAB_SWITCH: 'tab_switch',
  WINDOW_BLUR: 'window_blur',
  COPY_PASTE: 'copy_paste',
  PAGE_HIDDEN: 'page_hidden',
  FRAME_SAMPLE: 'frame_sample',
  SCREENSHOT: 'screenshot',
  ANSWER_SUBMIT: 'answer_submit',
  FORBIDDEN_SITE: 'forbidden_site',
};

function buildMessage(type, sessionId, payload = {}) {
  return {
    v: PROTOCOL_VERSION,
    type,
    session_id: sessionId,
    ts: new Date().toISOString(),
    payload,
  };
}

function validateMessage(msg) {
  return msg && msg.v === PROTOCOL_VERSION && msg.type && msg.session_id;
}

// Service worker global
if (typeof self !== 'undefined') {
  self.EXAMGUARD_PROTOCOL = {
    PROTOCOL_VERSION,
    EVENT_TYPES,
    buildMessage,
    validateMessage,
  };
}
