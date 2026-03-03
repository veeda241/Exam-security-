/**
 * ExamGuard Pro - Background Service Worker v2.0
 * Enhanced session management, robust error handling, and retry logic
 */

// ==================== CONFIGURATION ====================
const CONFIG = {
  API_BASE: 'http://localhost:8000/api',
  WS_URL: 'ws://localhost:8000/ws/student',
  SCREENSHOT_INTERVAL: 3000,
  WEBCAM_INTERVAL: 5000,
  SYNC_INTERVAL: 5000,        // Faster sync for real-time DB updates
  TRANSFORMER_INTERVAL: 8000, // Run transformer analysis every 8s
  MAX_RETRY_ATTEMPTS: 3,
  RETRY_DELAY: 2000,
};

// ==================== SESSION STATE ====================
let examSession = {
  active: false,
  sessionId: null,
  startTime: null,
  events: [],
  tabSwitchCount: 0,
  copyCount: 0,
  lastScreenCapture: null,
  lastWebcamCapture: null,
  lastSync: null,
};

let pendingStartData = null;
let captureWindowId = null;
let syncIntervalId = null;
let transformerIntervalId = null;
let wsConnection = null;
let wsReconnectTimer = null;
let clipboardTexts = [];     // Buffer for transformer analysis
let pendingAnalysis = [];    // Buffer for pending text analysis

// ==================== INITIALIZATION ====================

chrome.runtime.onInstalled.addListener(() => {
  console.log('🛡️ ExamGuard Pro v2.0 installed');
  chrome.storage.local.set({ examSession: null });
});

// Restore session on startup
chrome.storage.local.get(['examSession'], (result) => {
  if (result && result.examSession && result.examSession.active) {
    examSession = result.examSession;
    console.log('📂 Restored exam session:', examSession.sessionId);
    startPeriodicSync();
  }
});

// ==================== START FLOW ====================

async function handleStartExam(data) {
  pendingStartData = data;

  try {
    const window = await chrome.windows.create({
      url: chrome.runtime.getURL('capture-page.html'),
      type: 'popup',
      width: 650,
      height: 550,
      focused: true,
    });

    captureWindowId = window.id;
    return { success: true, waitingForCapture: true };
  } catch (error) {
    console.error('Failed to open capture window:', error);
    return { success: false, error: error.message };
  }
}

async function onCaptureReady(captureData) {
  if (!pendingStartData) {
    console.warn('No pending start data');
    return;
  }

  const result = await startExamSession(pendingStartData);

  if (result.success) {
    // Minimize capture window to keep streams alive
    if (captureWindowId) {
      chrome.windows.update(captureWindowId, { state: 'minimized' }).catch(() => { });
    }

    // Send success notification
    chrome.notifications.create({
      type: 'basic',
      iconUrl: 'icons/icon48.svg',
      title: '🛡️ ExamGuard Pro',
      message: 'Proctoring session started. Good luck!',
      priority: 2,
    });
  }

  pendingStartData = null;
}

// ==================== SESSION MANAGEMENT ====================

async function startExamSession(data) {
  try {
    let sessionId;

    // Try to create session on backend with retry
    for (let attempt = 1; attempt <= CONFIG.MAX_RETRY_ATTEMPTS; attempt++) {
      try {
        const response = await fetch(`${CONFIG.API_BASE}/students/create`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            student_id: data.studentId,
            exam_id: data.examId,
            student_name: data.studentName,
          }),
        });

        if (response.ok) {
          const result = await response.json();
          sessionId = result.session_id;
          console.log(`✅ Session created on attempt ${attempt}:`, sessionId);
          break;
        }
      } catch (error) {
        console.warn(`⚠️ Attempt ${attempt} failed:`, error.message);
        if (attempt < CONFIG.MAX_RETRY_ATTEMPTS) {
          await delay(CONFIG.RETRY_DELAY);
        }
      }
    }

    // Fallback to local session if backend unavailable
    if (!sessionId) {
      sessionId = `local-${Date.now()}-${randomId()}`;
      console.warn('⚠️ Using local session (backend unavailable)');
    }

    examSession = {
      active: true,
      sessionId: sessionId,
      startTime: Date.now(),
      events: [],
      tabSwitchCount: 0,
      copyCount: 0,
      lastScreenCapture: null,
      lastWebcamCapture: null,
      lastSync: null,
    };

    await chrome.storage.local.set({ examSession });

    // Notify all tabs
    notifyAllTabs('EXAM_STARTED');

    // Start periodic sync
    startPeriodicSync();

    console.log('✅ Exam session started:', sessionId);
    return { success: true, sessionId };

  } catch (error) {
    console.error('❌ Failed to start exam:', error);
    return { success: false, error: error.message };
  }
}

async function stopExamSession() {
  if (!examSession.active) {
    return { success: false, error: 'No active session' };
  }

  try {
    // Final sync
    await syncEvents();

    // End session on backend
    try {
      await fetch(`${CONFIG.API_BASE}/students/${examSession.sessionId}/end`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
    } catch (error) {
      console.warn('Backend session end failed:', error.message);
    }

    const summary = {
      sessionId: examSession.sessionId,
      duration: Date.now() - examSession.startTime,
      tabSwitchCount: examSession.tabSwitchCount,
      copyCount: examSession.copyCount,
      totalEvents: examSession.events.length,
    };

    // Reset session
    examSession = {
      active: false,
      sessionId: null,
      startTime: null,
      events: [],
      tabSwitchCount: 0,
      copyCount: 0,
      lastScreenCapture: null,
      lastWebcamCapture: null,
      lastSync: null,
    };

    await chrome.storage.local.set({ examSession: null });

    // Stop periodic sync
    stopPeriodicSync();

    // Notify all tabs
    notifyAllTabs('EXAM_STOPPED');

    // Close capture window
    if (captureWindowId) {
      chrome.windows.remove(captureWindowId).catch(() => { });
      captureWindowId = null;
    }

    chrome.notifications.create({
      type: 'basic',
      iconUrl: 'icons/icon48.svg',
      title: '🛡️ ExamGuard Pro',
      message: `Session ended. ${summary.totalEvents} events recorded.`,
      priority: 2,
    });

    console.log('🛑 Exam session ended');
    return { success: true, summary };

  } catch (error) {
    console.error('❌ Failed to stop exam:', error);
    return { success: false, error: error.message };
  }
}

// ==================== TAB MONITORING ====================

chrome.tabs.onActivated.addListener(async (activeInfo) => {
  if (!examSession.active) return;

  try {
    const tab = await chrome.tabs.get(activeInfo.tabId);

    logEvent({
      type: 'NAVIGATION',
      timestamp: Date.now(),
      data: {
        url: sanitizeUrl(tab.url),
        title: tab.title || 'Unknown',
        action: 'TAB_SWITCH',
      }
    });

    examSession.tabSwitchCount++;
    await saveSession();
  } catch (error) {
    console.warn('Tab monitoring error:', error.message);
  }
});

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (!examSession.active || !changeInfo.url) return;

  logEvent({
    type: 'NAVIGATION',
    timestamp: Date.now(),
    data: {
      url: sanitizeUrl(changeInfo.url),
      title: tab.title || 'Unknown',
      action: 'NAVIGATE',
    }
  });
});

chrome.windows.onFocusChanged.addListener((windowId) => {
  if (!examSession.active) return;

  if (windowId === chrome.windows.WINDOW_ID_NONE) {
    logEvent({
      type: 'WINDOW_BLUR',
      timestamp: Date.now(),
      data: { message: 'Browser lost focus' }
    });
  } else {
    logEvent({
      type: 'WINDOW_FOCUS',
      timestamp: Date.now(),
      data: { windowId }
    });
  }
});

// ==================== FULLSCREEN MONITORING ====================

// Monitor window state changes (maximized/fullscreen/normal)
chrome.windows.onBoundsChanged.addListener(debounce(checkFullscreen, 500));

async function checkFullscreen(windowId) {
  if (!examSession.active) return;

  try {
    const window = await chrome.windows.get(windowId);

    // Ignore devtools or popup windows if needed, but primarily check main exam window
    if (window.type === 'normal') {
      if (window.state !== 'fullscreen') {
        logEvent({
          type: 'FULLSCREEN_EXIT',
          timestamp: Date.now(),
          data: {
            state: window.state,
            message: 'User exited fullscreen mode'
          }
        });

        // Notify content script to show warning overlay
        chrome.tabs.query({ active: true, windowId: windowId }, (tabs) => {
          if (tabs[0]) {
            chrome.tabs.sendMessage(tabs[0].id, { type: 'FULLSCREEN_WARNING' }).catch(() => { });
          }
        });

        // Optional: Auto-enforce (Be careful with UX)
        // chrome.windows.update(windowId, { state: 'fullscreen' });
      } else {
        // Returned to fullscreen
        chrome.tabs.query({ active: true, windowId: windowId }, (tabs) => {
          if (tabs[0]) {
            chrome.tabs.sendMessage(tabs[0].id, { type: 'FULLSCREEN_RESTORED' }).catch(() => { });
          }
        });
      }
    }
  } catch (err) {
    // Window might have closed
  }
}

function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}



// ==================== MESSAGE HANDLING ====================

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  switch (message.type) {
    case 'START_EXAM':
      handleStartExam(message.data).then(sendResponse);
      return true;

    case 'CAPTURE_READY':
      onCaptureReady(message);
      sendResponse({ success: true });
      return true;

    case 'STOP_EXAM':
      stopExamSession().then(sendResponse);
      return true;

    case 'LOG_EVENT':
      logEvent(message.event);
      sendResponse({ success: true });
      return true;

    case 'GET_STATUS':
      sendResponse({
        active: examSession.active,
        sessionId: examSession.sessionId,
        tabSwitchCount: examSession.tabSwitchCount,
        copyCount: examSession.copyCount,
        eventCount: examSession.events.length,
        duration: examSession.startTime ? Date.now() - examSession.startTime : 0,
        lastScreenCapture: examSession.lastScreenCapture,
        lastWebcamCapture: examSession.lastWebcamCapture,
        lastSync: examSession.lastSync,
      });
      return true;

    case 'UPLOAD_SCREENSHOT':
      uploadScreenshot(message.data).then(sendResponse);
      return true;

    case 'UPLOAD_WEBCAM':
      uploadWebcamFrame(message.data).then(sendResponse);
      return true;

    // Handle webcam capture from webcam.js content script
    case 'WEBCAM_CAPTURE':
      if (examSession.active && message.data?.image) {
        uploadWebcamFrame(message.data.image).then(sendResponse);
      } else {
        sendResponse({ success: false, error: 'No active session' });
      }
      return true;

    // Handle screen capture from content.js
    case 'SCREEN_CAPTURE':
      if (examSession.active && message.data?.image) {
        uploadScreenshot(message.data.image).then(sendResponse);
      } else {
        sendResponse({ success: false, error: 'No active session' });
      }
      return true;

    // Handle clipboard text for transformer analysis
    case 'CLIPBOARD_TEXT':
      if (examSession.active && message.data?.text) {
        clipboardTexts.push({
          text: message.data.text,
          timestamp: message.data.timestamp || Date.now(),
        });
        // Immediately send for transformer analysis
        analyzeTextWithTransformer(message.data.text).then(sendResponse);
      } else {
        sendResponse({ success: false });
      }
      return true;
  }
});

// ==================== EVENT LOGGING ====================

function logEvent(event) {
  event.sessionId = examSession.sessionId;
  event.id = `evt-${Date.now()}-${randomId()}`;

  examSession.events.push(event);

  // Update specific counts
  if (event.type === 'COPY' || event.type === 'PASTE') {
    examSession.copyCount++;
  }

  // Trigger sync if queue is large
  if (examSession.events.length >= 20) {
    syncEvents();
  }

  console.log(`📝 [${event.type}]`, event.data?.url || event.data?.message || '');
}

// ==================== SYNC & UPLOADS ====================

async function syncEvents() {
  if (examSession.events.length === 0) return;

  try {
    const eventsToSync = [...examSession.events];

    const response = await fetch(`${CONFIG.API_BASE}/events/batch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: examSession.sessionId,
        events: eventsToSync,
      }),
    });

    if (response.ok) {
      // Clear synced events
      examSession.events = examSession.events.filter(e =>
        !eventsToSync.find(s => s.id === e.id)
      );
      examSession.lastSync = Date.now();
      await saveSession();
      console.log(`☁️ Synced ${eventsToSync.length} events`);
    }
  } catch (error) {
    console.warn('⚠️ Sync failed:', error.message);
  }
}

async function uploadScreenshot(dataUrl) {
  if (!examSession.active) {
    console.log('📸 Screenshot skipped - no active session');
    return { success: false };
  }

  console.log('📸 Uploading screenshot to backend...');

  try {
    const response = await fetch(`${CONFIG.API_BASE}/analysis/process`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: examSession.sessionId,
        timestamp: Date.now(),
        screen_image: dataUrl,
      }),
    });

    if (response.ok) {
      examSession.lastScreenCapture = Date.now();
      const result = await response.json();
      console.log('📸 Screenshot analysis result:', result);

      if (result.forbidden_detected) {
        logEvent({
          type: 'FORBIDDEN_CONTENT',
          timestamp: Date.now(),
          data: { keywords: result.detected_keywords },
        });
      }

      return { success: true, analysis: result };
    }
    console.warn('📸 Screenshot upload failed with status:', response.status);
    return { success: false };
  } catch (error) {
    console.warn('📸 Screenshot upload error:', error.message);
    return { success: false };
  }
}

async function uploadWebcamFrame(dataUrl) {
  if (!examSession.active) {
    console.log('📹 Webcam skipped - no active session');
    return { success: false };
  }

  console.log('📹 Uploading webcam frame to backend...');

  try {
    const response = await fetch(`${CONFIG.API_BASE}/analysis/process`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: examSession.sessionId,
        timestamp: Date.now(),
        webcam_image: dataUrl,
      }),
    });

    if (response.ok) {
      examSession.lastWebcamCapture = Date.now();
      const result = await response.json();
      console.log('📹 Webcam analysis result:', result);

      // CRITICAL: Check for phone detection - close Chrome immediately
      if (result.phone_detected) {
        console.log('🚨 PHONE DETECTED! Initiating shutdown...');
        logEvent({
          type: 'PHONE_DETECTED',
          timestamp: Date.now(),
          data: {
            message: 'Phone detected - exam terminated',
            objects: result.detected_objects
          },
        });

        // Show warning notification
        chrome.notifications.create({
          type: 'basic',
          iconUrl: 'icons/icon48.svg',
          title: '🚨 EXAM VIOLATION DETECTED',
          message: 'Phone usage detected! Chrome will close in 3 seconds. Your session has been flagged.',
          priority: 2,
          requireInteraction: true,
        });

        // Final sync before closing
        await syncEvents();

        // End the session
        await stopExamSession();

        // Close all Chrome windows after 3 second delay
        setTimeout(async () => {
          await closeAllChromeWindows();
        }, 3000);

        return { success: true, analysis: result, violation: 'PHONE_DETECTED' };
      }

      if (!result.face_detected) {
        logEvent({
          type: 'FACE_ABSENT',
          timestamp: Date.now(),
          data: { confidence: result.confidence },
        });
      }

      return { success: true, analysis: result };
    }
    console.warn('📹 Webcam upload failed with status:', response.status);
    return { success: false };
  } catch (error) {
    console.warn('📹 Webcam upload error:', error.message);
    return { success: false };
  }
}

// Close all Chrome windows when phone is detected
async function closeAllChromeWindows() {
  try {
    const windows = await chrome.windows.getAll();
    for (const window of windows) {
      await chrome.windows.remove(window.id).catch(() => { });
    }
    console.log('🚨 All Chrome windows closed due to phone detection');
  } catch (error) {
    console.error('Failed to close windows:', error);
  }
}

// ==================== PERIODIC SYNC ====================

function startPeriodicSync() {
  if (syncIntervalId) return;

  // Frequent event sync to keep DB updated
  syncIntervalId = setInterval(() => {
    if (examSession.active && examSession.events.length > 0) {
      syncEvents();
    }
  }, CONFIG.SYNC_INTERVAL);

  // Periodic transformer analysis on accumulated clipboard text
  transformerIntervalId = setInterval(() => {
    if (examSession.active && clipboardTexts.length > 0) {
      runBatchTransformerAnalysis();
    }
  }, CONFIG.TRANSFORMER_INTERVAL);

  // Connect WebSocket for real-time bidirectional communication
  connectWebSocket();
}

function stopPeriodicSync() {
  if (syncIntervalId) {
    clearInterval(syncIntervalId);
    syncIntervalId = null;
  }
  if (transformerIntervalId) {
    clearInterval(transformerIntervalId);
    transformerIntervalId = null;
  }
  disconnectWebSocket();
}

// ==================== WEBSOCKET CONNECTION ====================

function connectWebSocket() {
  if (wsConnection) return;

  const studentId = examSession.sessionId || 'unknown';
  const wsUrl = `${CONFIG.WS_URL}/${studentId}?session_id=${examSession.sessionId}`;

  try {
    wsConnection = new WebSocket(wsUrl);

    wsConnection.onopen = () => {
      console.log('🔌 WebSocket connected to backend');
      // Send initial session info
      wsConnection.send(JSON.stringify({
        type: 'session_info',
        session_id: examSession.sessionId,
        student_id: studentId,
      }));
    };

    wsConnection.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        handleServerMessage(data);
      } catch (e) {
        // Non-JSON message (like pong)
      }
    };

    wsConnection.onclose = () => {
      console.log('🔌 WebSocket disconnected');
      wsConnection = null;
      // Auto-reconnect if session still active
      if (examSession.active) {
        wsReconnectTimer = setTimeout(connectWebSocket, 3000);
      }
    };

    wsConnection.onerror = (error) => {
      console.warn('🔌 WebSocket error:', error);
    };
  } catch (e) {
    console.warn('🔌 WebSocket connection failed:', e);
  }
}

function disconnectWebSocket() {
  if (wsReconnectTimer) {
    clearTimeout(wsReconnectTimer);
    wsReconnectTimer = null;
  }
  if (wsConnection) {
    wsConnection.close();
    wsConnection = null;
  }
}

function handleServerMessage(data) {
  // Handle real-time commands from dashboard/proctor
  switch (data.type) {
    case 'proctor_alert':
      // Show alert from proctor to student
      chrome.notifications.create({
        type: 'basic',
        iconUrl: 'icons/icon48.svg',
        title: '⚠️ Proctor Alert',
        message: data.data?.message || 'Please focus on your exam.',
        priority: 2,
      });
      notifyAllTabs('PROCTOR_ALERT');
      break;

    case 'risk_score_update':
      console.log(`📊 Risk score updated: ${data.data?.risk_score}`);
      break;

    case 'force_end':
      // Proctor forced session end
      stopExamSession();
      break;

    default:
      break;
  }
}

// Send event via WebSocket for immediate dashboard update
function sendViaWebSocket(eventData) {
  if (wsConnection && wsConnection.readyState === WebSocket.OPEN) {
    wsConnection.send(`event:${JSON.stringify(eventData)}`);
    return true;
  }
  return false;
}

// ==================== TRANSFORMER ANALYSIS ====================

async function analyzeTextWithTransformer(text) {
  if (!text || text.length < 10) return { success: false, reason: 'text_too_short' };

  try {
    const response = await fetch(`${CONFIG.API_BASE}/analysis/transformer/similarity`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text: text,
        compare_texts: [
          'The answer can be found by searching online',
          'According to the textbook the answer is',
          'Copy and paste from the internet',
        ],
      }),
    });

    if (response.ok) {
      const result = await response.json();
      console.log('🧠 Transformer analysis:', result);

      if (result.is_suspicious) {
        logEvent({
          type: 'TRANSFORMER_ALERT',
          timestamp: Date.now(),
          data: {
            similarity: result.max_similarity,
            text_preview: text.substring(0, 100),
            message: `High similarity detected: ${(result.max_similarity * 100).toFixed(1)}%`,
          },
        });

        // Send via WebSocket for immediate dashboard notification
        sendViaWebSocket({
          type: 'plagiarism_detected',
          session_id: examSession.sessionId,
          similarity: result.max_similarity,
        });
      }

      return { success: true, analysis: result };
    }
    return { success: false };
  } catch (error) {
    console.warn('🧠 Transformer analysis error:', error.message);
    return { success: false, error: error.message };
  }
}

async function runBatchTransformerAnalysis() {
  if (clipboardTexts.length === 0) return;

  // Take the accumulated clipboard texts
  const textsToAnalyze = [...clipboardTexts];
  clipboardTexts = [];

  // Combine short texts, analyze long ones individually
  const combined = textsToAnalyze.map(t => t.text).join('\n');

  if (combined.length > 20) {
    await analyzeTextWithTransformer(combined);
  }

  // Also cross-compare clipboard entries for suspicious patterns
  if (textsToAnalyze.length >= 2) {
    try {
      const response = await fetch(`${CONFIG.API_BASE}/analysis/transformer/cross-compare`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          answers: textsToAnalyze.map(t => t.text).filter(t => t.length > 10),
        }),
      });

      if (response.ok) {
        const result = await response.json();
        console.log('🧠 Cross-compare result:', result);

        if (result.suspicious_pairs && result.suspicious_pairs.length > 0) {
          logEvent({
            type: 'CROSS_COMPARE_ALERT',
            timestamp: Date.now(),
            data: {
              suspicious_pairs: result.suspicious_pairs,
              message: 'Similar text patterns detected across clipboard entries',
            },
          });
        }
      }
    } catch (error) {
      console.warn('🧠 Cross-compare error:', error.message);
    }
  }
}

// ==================== UTILITIES ====================

function randomId() {
  return Math.random().toString(36).substring(2, 11);
}

function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function sanitizeUrl(url) {
  try {
    const parsed = new URL(url);
    return `${parsed.protocol}//${parsed.hostname}${parsed.pathname}`;
  } catch {
    return url || 'unknown';
  }
}

async function saveSession() {
  await chrome.storage.local.set({ examSession });
}

function notifyAllTabs(messageType) {
  chrome.tabs.query({}, (tabs) => {
    tabs.forEach(tab => {
      chrome.tabs.sendMessage(tab.id, { type: messageType }).catch(() => { });
    });
  });
}
