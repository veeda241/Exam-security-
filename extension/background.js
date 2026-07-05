/**
 * ExamGuard Pro - Background Service Worker v2.0
 * Enhanced session management, robust error handling, and retry logic
 */

try { importScripts('lib/protocol.js'); } catch (e) { console.warn('Protocol load failed', e); }

// ==================== CONFIGURATION ====================
const BACKEND_URL = 'http://127.0.0.1:8000';

const CONFIG = {
  API_BASE: `${BACKEND_URL}/api/v1`,
  API_LEGACY: `${BACKEND_URL}/api`,
  WS_URL: `${BACKEND_URL.replace('http://', 'ws://').replace('https://', 'wss://')}/api/v1/ws`,
  SYNC_INTERVAL: 3000,
  TRANSFORMER_INTERVAL: 15000,
  MAX_RETRY_ATTEMPTS: 3,
  RETRY_DELAY: 2000,
};

async function getAccessToken() {
  return new Promise((resolve) => {
    chrome.storage.session.get(['access_token'], (r) => resolve(r.access_token || null));
  });
}

async function setAccessToken(token) {
  return chrome.storage.session.set({ access_token: token });
}

async function postV2Event(sessionId, type, payload) {
  const token = await getAccessToken();
  const proto = self.EXAMGUARD_PROTOCOL;
  const body = proto
    ? proto.buildMessage(type, sessionId, payload)
    : { session_id: sessionId, type, payload, ts: new Date().toISOString() };

  const headers = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  try {
    const res = await fetch(`${CONFIG.API_BASE}/events/`, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
    });
    return res.ok ? await res.json() : null;
  } catch (err) {
    console.warn('[V2] Event post failed:', err);
    return null;
  }
}

// ==================== SESSION STATE ====================
let examSession = {
  active: false,
  sessionId: null,
  studentId: '',
  studentName: '',
  examId: '',
  startTime: null,
  events: [],
  tabSwitchCount: 0,
  copyCount: 0,
  nofaceCount: 0,
  multifaceCount: 0,
  phoneCount: 0,
  audioAnomalyCount: 0,
  lastScreenCapture: null,
  lastWebcamCapture: null,
  lastSync: null,
  globalRiskScore: 0,
  globalEffortScore: 100,
};

let pendingStartData = null;
let captureWindowId = null;
let syncIntervalId = null;
let transformerIntervalId = null;
let wsConnection = null;
let wsReconnectTimer = null;
let wsConnecting = false;
let wsReconnectDelayMs = 3000;
let clipboardTexts = [];     // Buffer for transformer analysis
let pendingAnalysis = [];    // Buffer for pending text analysis
let domCaptureIntervalId = null;
let webcamCaptureIntervalId = null;
let webcamAnalysisIntervalId = null;
let webcamUploadInFlight = false;

const LIVE_CAPTURE_INTERVAL_MS = 900;
const AI_ANALYSIS_INTERVAL_MS = 5000;

// ==================== MESSAGE HANDLING (REGISTER EARLY) ====================
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log('✉️ Received message:', message.type);
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

    case 'GET_STATUS': {
      const browsingStats = examSession.active ? browsingTracker.getStats() : null;
      sendResponse({
        active: examSession.active,
        sessionId: examSession.sessionId,
        tabSwitchCount: examSession.tabSwitchCount,
        copyCount: examSession.copyCount,
        nofaceCount: examSession.nofaceCount,
        multifaceCount: examSession.multifaceCount,
        phoneCount: examSession.phoneCount,
        audioAnomalyCount: examSession.audioAnomalyCount,
        eventCount: examSession.events.length,
        duration: examSession.startTime ? Date.now() - examSession.startTime : 0,
        lastScreenCapture: examSession.lastScreenCapture,
        lastWebcamCapture: examSession.lastWebcamCapture,
        lastSync: examSession.lastSync,
        globalRiskScore: browsingStats?.browsingRiskScore ?? examSession.globalRiskScore ?? 0,
        globalEffortScore: browsingStats?.effortScore ?? examSession.globalEffortScore ?? 100,
        browsing: browsingStats,
      });
      return true;
    }


    case 'CLIPBOARD_TEXT':
      if (examSession.active && message.data?.text) {
        clipboardTexts.push({
          text: message.data.text,
          timestamp: message.data.timestamp || Date.now(),
        });
        analyzeTextWithTransformer(message.data.text).catch(console.warn);
        sendResponse({ success: true, queued: true });
      } else {
        sendResponse({ success: false });
      }
      return true;

    case 'DOM_CONTENT_CAPTURE':
      if (examSession.active && message.data?.image) {
        uploadDOMSnapshot(message.data).catch(console.warn);
        sendResponse({ success: true, queued: true });
      } else {
        sendResponse({ success: false });
      }
      return true;

    case 'PAGE_CONTEXT':
      if (examSession.active && (message.data?.url || message.data?.title)) {
        analyzePageContext(message.data).catch(console.warn);
        sendResponse({ success: true, queued: true });
      } else {
        sendResponse({ success: false });
      }
      return true;

    case 'BEHAVIOR_ALERT':
      if (examSession.active) {
        logEvent({
          type: message.data?.type || 'BEHAVIOR_ALERT',
          data: message.data || {},
          timestamp: Date.now()
        });
      }
      sendResponse({ success: true });
      return true;

    case 'NETWORK_INFO':
      // Simply ack it without logging for now
      sendResponse({ success: true });
      return true;

    case 'WEBCAM_CAPTURE':
      if (examSession.active && message.data?.image) {
        uploadWebcamFrame(message.data.image).catch(console.warn);
        sendResponse({ success: true });
      } else {
        sendResponse({ success: false });
      }
      return true;

    default:
      console.log('❓ Unknown message type:', message.type);
      sendResponse({ success: false, error: 'Unknown message type' });
      return false;
  }
});

// ==================== BROWSING TRACKER ====================
/**
 * BrowsingTracker uses chrome.tabs API to monitor:
 *  - Which website is currently active and for how long
 *  - Time spent per site category (exam, AI, cheating, entertainment, other)
 *  - All open tabs (periodic audit via chrome.tabs.query)
 *  - Real-time risk & effort scores based on browsing behavior
 */
function isProductiveCategory(category) {
  return ['exam', 'quiz', 'education', 'learning'].includes(String(category || '').toLowerCase());
}

function isHighRiskLevel(riskLevel) {
  return ['high', 'critical', 'medium'].includes(String(riskLevel || '').toLowerCase());
}

function syncExamSessionScoresFromBrowsing() {
  if (!examSession.active) return;
  examSession.globalRiskScore = Math.max(
    examSession.globalRiskScore || 0,
    browsingTracker.browsingRiskScore || 0
  );
  examSession.globalEffortScore = browsingTracker.effortScore ?? examSession.globalEffortScore ?? 100;
}

const browsingTracker = {
  activeSite: null,            // { url, title, tabId, category, startTime }
  
  // Time spent per category (milliseconds)
  timeByCategory: {
    exam: 0,
    quiz: 0,
    education: 0,
    learning: 0,
    ai: 0,
    cheating: 0,
    entertainment: 0,
    social: 0,
    other: 0,
  },
  
  // All visited sites with durations
  visitedSites: [],            // [{ url, title, category, riskLevel, firstVisit, totalTime, visitCount }]
  
  // Open tabs snapshot (last audit)
  openTabs: [],                // [{ tabId, url, title, category, riskLevel }]
  
  // Calculated scores
  browsingRiskScore: 0,        // 0-100 based on sites visited
  effortScore: 100,            // 0-100 based on time on task vs distractions
  
  // Audit interval
  auditIntervalId: null,
  timeFlushIntervalId: null,

  getProductiveTimeMs() {
    return (
      (this.timeByCategory.exam || 0) +
      (this.timeByCategory.quiz || 0) +
      (this.timeByCategory.education || 0) +
      (this.timeByCategory.learning || 0)
    );
  },

  getExamFocusPercent() {
    this.flushActiveSite();
    const totalTime = Object.values(this.timeByCategory).reduce((a, b) => a + b, 0);
    const productiveTime = this.getProductiveTimeMs();

    if (totalTime <= 0) {
      if (this.activeSite && isProductiveCategory(this.activeSite.category)) {
        return 100;
      }
      return 0;
    }

    return Math.min(100, Math.round((productiveTime / totalTime) * 100));
  },

  /** Track the currently focused exam tab when session starts */
  async syncActiveTab() {
    if (!examSession.active) return;

    try {
      const tabs = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
      const tab = tabs.find(
        (t) =>
          t?.url &&
          !t.url.startsWith('chrome://') &&
          !t.url.startsWith('chrome-extension://') &&
          !isInternalCaptureUrl(t.url)
      );

      if (!tab) return;

      const cleanUrl = sanitizeUrl(tab.url);
      if (this.activeSite?.url === cleanUrl && this.activeSite?.tabId === tab.id) {
        return;
      }

      this.trackSiteChange(tab.id, tab.url, tab.title);
    } catch (error) {
      console.warn('Active tab sync failed:', error.message);
    }
  },

  /** Start tracking when exam begins */
  start() {
    this.reset();
    this.syncActiveTab();
    this.auditOpenTabs();
    this.auditIntervalId = setInterval(() => this.auditOpenTabs(), 10000);
    // Accrue time every 2s even without tab switches or popup open
    this.timeFlushIntervalId = setInterval(() => {
      if (!examSession.active) return;
      this.flushActiveSite();
      this.calculateScores();
      syncExamSessionScoresFromBrowsing();
    }, 2000);
  },

  /** Stop tracking when exam ends */
  stop() {
    this.flushActiveSite();
    if (this.timeFlushIntervalId) {
      clearInterval(this.timeFlushIntervalId);
      this.timeFlushIntervalId = null;
    }
    if (this.auditIntervalId) {
      clearInterval(this.auditIntervalId);
      this.auditIntervalId = null;
    }
  },
  
  /** Reset all tracking data */
  reset() {
    this.activeSite = null;
    this.timeByCategory = {
      exam: 0, quiz: 0, education: 0, learning: 0,
      ai: 0, cheating: 0, entertainment: 0, social: 0, other: 0,
    };
    this.visitedSites = [];
    this.openTabs = [];
    this.browsingRiskScore = 0;
    this.effortScore = 100;
  },
  
  /** Apply server/model classification to active site and scores */
  applyModelClassification(url, classification) {
    if (!classification || !url) return;
    const cleanUrl = sanitizeUrl(url);
    const trackerCategory = (
      classification.trackerCategory ||
      classification.tracker_category ||
      classification.category ||
      'other'
    ).toLowerCase();
    const riskLevel = classification.riskLevel || classification.risk_level || 'none';

    if (this.activeSite && this.activeSite.url === cleanUrl) {
      if (this.activeSite.category !== trackerCategory) {
        this.flushActiveSite();
      }
      this.activeSite.category = trackerCategory;
      this.activeSite.riskLevel = riskLevel;
      if (!this.activeSite.startTime) {
        this.activeSite.startTime = Date.now();
      }
    }

    const entry = this.visitedSites.find((s) => s.url === cleanUrl);
    if (entry) {
      entry.category = trackerCategory;
      entry.riskLevel = riskLevel;
    }

    const tabEntry = this.openTabs.find((t) => t.url === cleanUrl);
    if (tabEntry) {
      tabEntry.category = trackerCategory;
      tabEntry.riskLevel = riskLevel;
    }

    this.calculateScores();
    pushSessionScores();
  },

  /** Called when user switches to a new tab or navigates to a new URL */
  trackSiteChange(tabId, url, title) {
    // Flush time for the previous active site
    this.flushActiveSite();

    // Initial classification (cache / title heuristic / local exam only)
    const classification = classifyUrl(url, title);
    let category = 'other';
    let riskLevel = 'none';
    if (classification) {
      category = (
        classification.trackerCategory ||
        classification.category ||
        'other'
      ).toLowerCase();
      riskLevel = classification.riskLevel || 'none';
    } else if (isLocalExamPlatform(url)) {
      category = 'exam';
    }

    // Set new active site
    this.activeSite = {
      url: sanitizeUrl(url),
      title: title || 'Unknown',
      tabId,
      category,
      riskLevel,
      startTime: Date.now(),
    };

    // Layer 1 Cross-check: Exam Question Leak detection
    this.checkForQuestionLeads(url, category);

    // Update visited sites list
    this.recordVisit(url, title, category, riskLevel);

    // Recalculate scores
    this.calculateScores();
    pushSessionScores();

    // Refine with content/JS model (no domain lists)
    classifyPageWithModel({ url, title })
      .then((refined) => {
        if (!refined || !this.activeSite) return;
        if (this.activeSite.url !== sanitizeUrl(url)) return;
        this.applyModelClassification(url, refined);
      })
      .catch(() => {});
  },

  /** Track visual presence (from html2canvas) */
  trackVisualEngagement(data) {
    if (!this.activeSite) return;
    
    // Check if what was captured is actually the exam page
    const isActuallyExam = this.isExamRelated(data.url);
    if (isActuallyExam || isProductiveCategory(this.activeSite?.category)) {
        this.effortScore = Math.min(100, this.effortScore + 8);
        syncExamSessionScoresFromBrowsing();
        console.log('📈 Visual focus on productive page confirmed');
    } else if (this.activeSite?.category === 'other') {
        this.browsingRiskScore = Math.min(100, this.browsingRiskScore + 8);
        syncExamSessionScoresFromBrowsing();
        console.log('📉 Visual activity on unclassified site');
    } else {
        const classification = classifyUrl(data.url);
        if (classification && isHighRiskLevel(classification.riskLevel)) {
            this.browsingRiskScore = Math.min(100, this.browsingRiskScore + 10);
            console.log(`📉 Visual risk on forbidden site: ${classification.category}`);
        }
    }
  },

  checkForQuestionLeads(url, category) {
    if (!examSession.latestExamQuestion || category === 'exam') return;

    const lowerUrl = url.toLowerCase();
    const questionKeywords = examSession.latestExamQuestion.toLowerCase()
        .split(/\W+/)
        .filter(k => k.length > 5); // Focus on meaningful words

    // Check if 3+ long keywords from the exam question appear in the URL (typical Googling)
    const matches = questionKeywords.filter(k => lowerUrl.includes(k));
    if (matches.length >= 3) {
        logEvent({
            type: 'EXAM_QUESTION_LEAK_DETECTION',
            timestamp: Date.now(),
            data: {
                screenshotIntervalMs: 2500,
              webcamIntervalMs: 2500,
                url, 
                matches: matches.slice(0, 5),
                message: 'Exam question text detected in browser URL query (Googling detected)' 
            }
        });

        sendViaWebSocket({
            type: 'question_leak_alert',
            session_id: examSession.sessionId,
            url,
            matched_keywords: matches
        });
    }
  },
  
  /** Flush accumulated time for the currently active site */
  flushActiveSite() {
    if (!this.activeSite || !this.activeSite.startTime) return;
    
    const elapsed = Date.now() - this.activeSite.startTime;
    const cat = this.activeSite.category;
    if (this.timeByCategory.hasOwnProperty(cat)) {
      this.timeByCategory[cat] += elapsed;
    } else {
      this.timeByCategory.other += elapsed;
    }
    
    // Also update totalTime in visitedSites
    const cleanUrl = this.activeSite.url;
    const entry = this.visitedSites.find(s => s.url === cleanUrl);
    if (entry) {
      entry.totalTime += elapsed;
      entry.lastVisit = Date.now();
    }
    
    this.activeSite.startTime = Date.now(); // Reset for next flush
  },
  
  /** Record a visit to a specific site */
  recordVisit(url, title, category, riskLevel) {
    const cleanUrl = sanitizeUrl(url);
    const existing = this.visitedSites.find(s => s.url === cleanUrl);
    if (existing) {
      existing.visitCount++;
      existing.lastVisit = Date.now();
    } else {
      this.visitedSites.push({
        url: cleanUrl,
        title: title || 'Unknown',
        category,
        riskLevel,
        firstVisit: Date.now(),
        lastVisit: Date.now(),
        totalTime: 0,
        visitCount: 1,
      });
    }
  },
  
  /** Check if URL is the local exam dashboard (instant detect only — no domain lists) */
  isExamRelated(url) {
    return isLocalExamPlatform(url);
  },
  
  /** Audit all currently open tabs using chrome.tabs.query */
  async auditOpenTabs() {
    if (!examSession.active) return;
    
    try {
      const tabs = await chrome.tabs.query({});
      const auditResults = [];
      let flaggedCount = 0;
      
      for (const tab of tabs) {
        if (!tab.url || tab.url.startsWith('chrome://') || tab.url.startsWith('chrome-extension://')) {
          continue;
        }
        
        const classification = classifyUrl(tab.url, tab.title);
        const entry = {
          tabId: tab.id,
          url: sanitizeUrl(tab.url),
          title: tab.title || 'Unknown',
          category: classification
            ? (classification.trackerCategory || classification.category || 'other').toLowerCase()
            : (isLocalExamPlatform(tab.url) ? 'exam' : 'other'),
          riskLevel: classification ? classification.riskLevel : 'none',
          active: tab.active,
          pinned: tab.pinned,
        };

        auditResults.push(entry);
        if (classification && isHighRiskLevel(classification.riskLevel)) flaggedCount++;

        classifyPageWithModel({ url: tab.url, title: tab.title })
          .then((refined) => {
            if (!refined) return;
            const idx = this.openTabs.findIndex((t) => t.tabId === tab.id);
            if (idx === -1) return;
            this.openTabs[idx].category = (
              refined.trackerCategory || refined.category || 'other'
            ).toLowerCase();
            this.openTabs[idx].riskLevel = refined.riskLevel || 'none';
            this.calculateScores();
            pushSessionScores();
          })
          .catch(() => {});
        
        // Record visit if not already tracked
        this.recordVisit(tab.url, tab.title, entry.category.toLowerCase(), entry.riskLevel);
      }
      
      this.openTabs = auditResults;
      
      // Log audit event if flagged tabs found
      if (flaggedCount > 0) {
        logEvent({
          type: 'TAB_AUDIT',
          timestamp: Date.now(),
          data: {
            totalTabs: auditResults.length,
            flaggedTabs: flaggedCount,
            flaggedUrls: auditResults.filter(t => t.riskLevel !== 'none').map(t => ({
              url: t.url, category: t.category, riskLevel: t.riskLevel
            })),
            message: `Tab audit: ${flaggedCount} flagged out of ${auditResults.length} tabs`,
          }
        });
      }
      
      this.calculateScores();
      pushSessionScores();
    } catch (error) {
      console.warn('Tab audit error:', error.message);
    }
  },
  
  /** Calculate browsing risk and effort scores */
  calculateScores() {
    // Flush current active site to get accurate totals
    this.flushActiveSite();
    
    const totalTime = Object.values(this.timeByCategory).reduce((a, b) => a + b, 0) || 1;
    
    // --- Browsing Risk Score (0-100) ---
    // Based on: time on forbidden sites, number of flagged sites, open flagged tabs
    let risk = 0;
    
    // Time-based risk
    const aiTimeRatio = this.timeByCategory.ai / totalTime;
    const cheatingTimeRatio = this.timeByCategory.cheating / totalTime;
    const entertainmentTimeRatio = this.timeByCategory.entertainment / totalTime;
    const socialTimeRatio = this.timeByCategory.social / totalTime;
    const otherTimeRatio = this.timeByCategory.other / totalTime;
    
    risk += aiTimeRatio * 50;
    risk += cheatingTimeRatio * 100;
    risk += entertainmentTimeRatio * 100;
    risk += socialTimeRatio * 70;
    // Unclassified "other" sites raise risk — unknown browsing is suspicious
    risk += otherTimeRatio * 70;

    const flaggedCategories = ['ai', 'cheating', 'entertainment', 'social'];
    const flaggedSites = this.visitedSites.filter(s => flaggedCategories.includes(s.category));
    risk += Math.min(flaggedSites.length * 15, 60);

    const otherSites = this.visitedSites.filter((s) => s.category === 'other');
    risk += Math.min(otherSites.length * 12, 45);
    
    // Open tabs risk bonus (only meaningful risk levels)
    const flaggedOpenTabs = this.openTabs.filter((t) => isHighRiskLevel(t.riskLevel)).length;
    risk += Math.min(flaggedOpenTabs * 10, 40);

    // Immediate risk when active tab is high-risk or unclassified
    if (this.activeSite && isHighRiskLevel(this.activeSite.riskLevel)) {
      risk += 25;
    }
    if (this.activeSite?.category === 'other') {
      risk += 25;
    }

    this.browsingRiskScore = Math.min(Math.round(risk), 100);
    
    // --- Effort Score (0-100) ---
    // Effort rises on exam, quiz, LMS, and exam-related search; "other" does not help
    const productiveTime = this.getProductiveTimeMs();
    const productiveRatio = productiveTime / totalTime;

    let effort = 15;
    effort += (this.timeByCategory.exam / totalTime) * 45;
    effort += (this.timeByCategory.quiz / totalTime) * 42;
    effort += (this.timeByCategory.education / totalTime) * 42;
    effort += (this.timeByCategory.learning / totalTime) * 38;

    if (this.activeSite && isProductiveCategory(this.activeSite.category)) {
      effort += 15;
    }

    if (productiveRatio > 0.45) effort += 8;
    if (productiveRatio > 0.7) effort += 12;

    // Penalize time on unknown/unclassified sites
    effort -= otherTimeRatio * 30;

    this.effortScore = Math.min(Math.max(Math.round(effort), 0), 100);
    syncExamSessionScoresFromBrowsing();
  },
  
  /** Generate a browsing summary event for syncing to server */
  generateSummaryEvent() {
    this.flushActiveSite();
    this.calculateScores();
    
    const totalTime = Object.values(this.timeByCategory).reduce((a, b) => a + b, 0);
    const productiveTime = this.getProductiveTimeMs();
    const examFocusPercent = this.getExamFocusPercent();
    
    return {
      type: 'BROWSING_SUMMARY',
      timestamp: Date.now(),
      data: {
        activeSite: this.activeSite ? {
          url: this.activeSite.url,
          title: this.activeSite.title,
          category: this.activeSite.category,
          riskLevel: this.activeSite.riskLevel,
        } : null,
        timeByCategory: { ...this.timeByCategory },
        totalTime,
        browsingRiskScore: this.browsingRiskScore,
        effortScore: this.effortScore,
        uniqueSitesVisited: this.visitedSites.length,
        flaggedSitesCount: this.visitedSites.filter(s => ['ai', 'cheating', 'entertainment', 'social'].includes(s.category)).length,
        openTabsCount: this.openTabs.length,
        flaggedOpenTabs: this.openTabs.filter((t) => isHighRiskLevel(t.riskLevel)).length,
        topFlaggedSites: this.visitedSites
          .filter(s => ['ai', 'cheating', 'entertainment'].includes(s.category))
          .sort((a, b) => b.totalTime - a.totalTime)
          .slice(0, 10)
          .map(s => ({
            url: s.url,
            category: s.category,
            riskLevel: s.riskLevel,
            totalTime: s.totalTime,
            visitCount: s.visitCount,
          })),
        examTimePercent: examFocusPercent,
        examFocusPercent,
        distractionTimePercent: totalTime > 0 ? Math.round(
          ((this.timeByCategory.ai + this.timeByCategory.cheating +
            this.timeByCategory.entertainment + this.timeByCategory.social +
            this.timeByCategory.other) / totalTime) * 100
        ) : 0,
      },
    };
  },
  
  /** Get current stats for the popup */
  getStats() {
    this.flushActiveSite();
    this.calculateScores();

    const totalTime = Object.values(this.timeByCategory).reduce((a, b) => a + b, 0);
    const examFocusPercent = this.getExamFocusPercent();

    return {
      activeSite: this.activeSite ? {
        url: this.activeSite.url,
        category: this.activeSite.category,
        riskLevel: this.activeSite.riskLevel,
      } : null,
      timeByCategory: { ...this.timeByCategory },
      totalTime,
      examFocusPercent,
      examTimePercent: examFocusPercent,
      browsingRiskScore: this.browsingRiskScore,
      effortScore: this.effortScore,
      flaggedSitesCount: this.visitedSites.filter(s => ['ai', 'cheating', 'entertainment', 'social'].includes(s.category)).length,
      totalSitesVisited: this.visitedSites.length,
      openTabsCount: this.openTabs.length,
      flaggedOpenTabs: this.openTabs.filter((t) => isHighRiskLevel(t.riskLevel)).length,
      currentCategory: this.activeSite?.category || 'none',
    };
  },
};

// ==================== PAGE CLASSIFICATION (content/JS model — no domain lists) ====================
const pageClassificationCache = new Map();
const PAGE_CLASSIFY_CACHE_TTL_MS = 120000;

function isLocalExamPlatform(url) {
  if (!url) return false;
  try {
    const host = new URL(url).hostname.replace(/^www\./, '').toLowerCase();
    return host === 'localhost' || host === '127.0.0.1' || host.includes('examguard');
  } catch {
    return false;
  }
}

function pageClassifyCacheKey(url, title) {
  return `${sanitizeUrl(url)}|${String(title || '').slice(0, 80).toLowerCase()}`;
}

/** Detect academic/exam-related web search (Google, Bing, etc.) */
function isExamRelatedSearch(url, title = '') {
  const combined = `${url} ${title}`.toLowerCase();
  if (!/(\/search|[?&]q=|google\.[^/]+\/search|bing\.com\/search|duckduckgo\.com)/.test(combined)) {
    return false;
  }

  const studyPattern = /\b(exam|quiz|assignment|syllabus|lecture|homework|study|course|practice|textbook|notes|tutorial|problem set|lab report)\b/;

  try {
    const parsed = new URL(url);
    const query = decodeURIComponent(parsed.searchParams.get('q') || parsed.searchParams.get('query') || '');
    return studyPattern.test(`${query} ${title}`.toLowerCase());
  } catch {
    return studyPattern.test(combined);
  }
}

/** Lightweight title/URL text heuristic until full page content arrives */
function titleHeuristicClassification(url, title = '') {
  const combined = `${url} ${title}`.toLowerCase();

  if (isLocalExamPlatform(url)) {
    return {
      category: 'EXAM',
      trackerCategory: 'exam',
      site: 'local exam platform',
      riskLevel: 'none',
      method: 'local',
    };
  }

  if (isExamRelatedSearch(url, title)) {
    return {
      category: 'LEARNING',
      trackerCategory: 'learning',
      site: 'exam search',
      riskLevel: 'none',
      method: 'exam_search',
    };
  }

  const patterns = [
    { re: /\b(kahoot|quizizz|quizlet live|socrative|nearpod|start quiz|submit quiz|question \d+ of)\b/, category: 'QUIZ', trackerCategory: 'quiz', riskLevel: 'none' },
    { re: /\b(my courses|course dashboard|google classroom|canvas|moodle|blackboard|coursera|udemy|khan academy|edx|codecademy)\b/, category: 'EDUCATION', trackerCategory: 'education', riskLevel: 'none' },
    { re: /\b(chatgpt|openai|claude|gemini|copilot|perplexity|deepseek|llm|ai chat)\b/, category: 'AI', trackerCategory: 'ai', riskLevel: 'high' },
    { re: /\b(chegg|course hero|studocu|answer key|homework help|essay writer|solution manual)\b/, category: 'CHEATING', trackerCategory: 'cheating', riskLevel: 'critical' },
    { re: /\b(youtube|netflix|twitch|tiktok|watch now|episode|gaming|stream live)\b/, category: 'ENTERTAINMENT', trackerCategory: 'entertainment', riskLevel: 'critical' },
    { re: /\b(facebook|instagram|reddit|discord|twitter|timeline|news feed)\b/, category: 'SOCIAL', trackerCategory: 'social', riskLevel: 'medium' },
    { re: /\b(tutorial|documentation|stackoverflow|leetcode|wikipedia|course module|lecture)\b/, category: 'LEARNING', trackerCategory: 'learning', riskLevel: 'none' },
    { re: /\b(proctor|lockdown|submit exam|quiz attempt|assessment portal|gradescope)\b/, category: 'EXAM', trackerCategory: 'exam', riskLevel: 'none' },
  ];

  for (const pattern of patterns) {
    if (pattern.re.test(combined)) {
      return {
        category: pattern.category,
        trackerCategory: pattern.trackerCategory,
        site: (title || url).slice(0, 60),
        riskLevel: pattern.riskLevel,
        method: 'title_heuristic',
      };
    }
  }

  return null;
}

/** Classify page via server content/JS model */
async function classifyPageWithModel({ url, title = '', content = '', signals = {} }) {
  if (!url) return null;

  const key = pageClassifyCacheKey(url, title);
  const cached = pageClassificationCache.get(key);
  if (cached && Date.now() - cached.at < PAGE_CLASSIFY_CACHE_TTL_MS) {
    return cached.result;
  }

  const quick = titleHeuristicClassification(url, title);
  if (quick && quick.method === 'local') {
    pageClassificationCache.set(key, { at: Date.now(), result: quick });
    return quick;
  }

  try {
    const response = await fetch(`${CONFIG.API_BASE}/classify/page`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url, title, content, signals }),
    });

    if (response.ok) {
      const data = await response.json();
      const result = {
        category: data.category,
        trackerCategory: data.tracker_category || data.trackerCategory || 'other',
        site: data.site || (title || url).slice(0, 60),
        riskLevel: data.risk_level || data.riskLevel || 'low',
        riskScore: data.risk_score,
        effortScore: data.effort_score,
        confidence: data.confidence,
        method: data.method,
        reason: data.reason,
      };
      pageClassificationCache.set(key, { at: Date.now(), result });
      return result;
    }
  } catch (error) {
    console.warn('Page classify API failed:', error.message);
  }

  if (quick) {
    pageClassificationCache.set(key, { at: Date.now(), result: quick });
    return quick;
  }

  return {
    category: 'OTHER',
    trackerCategory: 'other',
    site: (title || url).slice(0, 60),
    riskLevel: 'low',
    method: 'fallback',
  };
}

/** Sync classify — uses cache or title heuristic only (tab switch hot path) */
function classifyUrl(url, title = '') {
  if (!url) return null;
  const key = pageClassifyCacheKey(url, title);
  const cached = pageClassificationCache.get(key);
  if (cached) return cached.result;
  return titleHeuristicClassification(url, title);
}

let lastScorePushAt = 0;
async function pushSessionScores(force = false) {
  if (!examSession.active || !examSession.sessionId) return;

  const now = Date.now();
  if (!force && now - lastScorePushAt < 2000) return;
  lastScorePushAt = now;

  const summary = browsingTracker.generateSummaryEvent();
  try {
    await fetch(`${CONFIG.API_BASE}/sessions/${examSession.sessionId}/scores`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(summary.data),
    });
  } catch (error) {
    console.warn('Score sync failed:', error.message);
  }
}

// ==================== INITIALIZATION ====================

chrome.runtime.onInstalled.addListener(() => {
  console.log('🛡️ ExamGuard Pro v2.0 installed');
  chrome.storage.local.set({ examSession: null });
});

// Restore session on startup
chrome.storage.local.get(['examSession'], (result) => {
  if (result && result.examSession && result.examSession.active) {
    examSession = result.examSession;

    // PREVENT MEMORY LEAK: Clean up if previously bloated
    if (examSession.events && examSession.events.length > 100) {
      examSession.events = examSession.events.slice(-50);
      saveSession(); // Resave the cleaned version
    }

    console.log('📂 Restored exam session:', examSession.sessionId);
    browsingTracker.start();
    startPeriodicSync();
  }
});

// ==================== START FLOW ====================
let activeStartPromise = null;

async function handleStartExam(data) {
  pendingStartData = data;
  
  // Use a promise-resolving mechanism to wait for the capture window to be ready
  return new Promise(async (resolve) => {
    activeStartPromise = resolve;
    
    try {
      const window = await chrome.windows.create({
        url: chrome.runtime.getURL('capture-page.html'),
        type: 'popup',
        width: 650,
        height: 550,
        focused: true,
      });

      captureWindowId = window.id;
      // We don't resolve here. We resolve in onCaptureReady.
    } catch (error) {
      console.error('Failed to open capture window:', error);
      activeStartPromise = null;
      resolve({ success: false, error: error.message });
    }
  });
}

async function onCaptureReady(captureData, sendResponse) {
  if (!pendingStartData) {
    console.warn('No pending start data');
    if (sendResponse) sendResponse({ success: false, error: 'No session data' });
    if (activeStartPromise) activeStartPromise({ success: false, error: 'No session data' });
    return;
  }

  const result = await startExamSession(pendingStartData);

  if (result.success) {
    // Keep the capture window alive without minimizing (minimized windows throttle video frames).
    if (captureWindowId) {
      chrome.windows.update(captureWindowId, { focused: false, drawAttention: false }).catch(() => { });
    }

    // Send success notification
    chrome.notifications.create({
      type: 'basic',
      iconUrl: 'icons/icon48.png',
      title: '🛡️ ExamGuard Pro',
      message: 'Proctoring session started. Good luck!',
      priority: 2,
    });
    
    if (sendResponse) sendResponse({ success: true });
    if (activeStartPromise) activeStartPromise({ success: true });
  } else {
    // If it failed, close the capture window too
    if (captureWindowId) {
      chrome.windows.remove(captureWindowId).catch(() => { });
    }
    if (sendResponse) sendResponse({ success: false, error: result.error });
    if (activeStartPromise) activeStartPromise({ success: false, error: result.error });
  }

  pendingStartData = null;
  activeStartPromise = null;
}

// ==================== SESSION MANAGEMENT ====================

async function startExamSession(data) {
  try {
    let sessionId;

    // 2. Try to create session on backend with retry
    let lastError = null;
    for (let attempt = 1; attempt <= CONFIG.MAX_RETRY_ATTEMPTS; attempt++) {
      try {
        const response = await fetch(`${CONFIG.API_BASE}/sessions/create`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            student_id: data.studentId,
            exam_id: data.examId,
            student_name: data.studentName,
          }),
        });

        const result = await response.json();

        if (response.ok) {
          sessionId = result.session_id;
          console.log(`✅ Session created on attempt ${attempt}:`, sessionId);
          break;
        } else {
          lastError = result.detail || `Server error (${response.status})`;
          console.warn(`⚠️ Attempt ${attempt} rejected by server:`, lastError);
          // If it's a validation error (like 400), don't retry
          if (response.status === 400) break;
        }
      } catch (error) {
        lastError = error.message;
        console.warn(`⚠️ Attempt ${attempt} network/timeout failed:`, lastError);
        if (attempt < CONFIG.MAX_RETRY_ATTEMPTS) {
          await delay(CONFIG.RETRY_DELAY);
        }
      }
    }

    // Fail if backend unavailable or rejected
    if (!sessionId) {
      console.error('❌ Failed to start session:', lastError);
      return { 
        success: false, 
        error: lastError || 'Backend unreachable. Check your connection or ask your proctor.' 
      };
    }

    examSession = {
      active: true,
      sessionId: sessionId,
      studentId: data.studentId || '',
      studentName: data.studentName || '',
      examId: data.examId || '',
      startTime: Date.now(),
      events: [],
      tabSwitchCount: 0,
      copyCount: 0,
      nofaceCount: 0,
      multifaceCount: 0,
      phoneCount: 0,
      audioAnomalyCount: 0,
      lastScreenCapture: null,
      lastWebcamCapture: null,
      lastSync: null,
      globalRiskScore: 0,
      globalEffortScore: 100,
    };

    await chrome.storage.local.set({ examSession });

    // Notify all tabs
    notifyAllTabs('EXAM_STARTED');

    // Start periodic sync
    browsingTracker.start();
    startPeriodicSync();

    if (webcamCaptureIntervalId) {
      clearInterval(webcamCaptureIntervalId);
      webcamCaptureIntervalId = null;
    }
    if (domCaptureIntervalId) {
      clearInterval(domCaptureIntervalId);
      domCaptureIntervalId = null;
    }
    if (webcamAnalysisIntervalId) {
      clearInterval(webcamAnalysisIntervalId);
      webcamAnalysisIntervalId = null;
    }
    webcamUploadInFlight = false;
    triggerNativeDOMCapture();
    triggerWebcamCapture();
    domCaptureIntervalId = setInterval(triggerNativeDOMCapture, LIVE_CAPTURE_INTERVAL_MS);
    webcamCaptureIntervalId = setInterval(triggerWebcamCapture, LIVE_CAPTURE_INTERVAL_MS);
    webcamAnalysisIntervalId = setInterval(triggerWebcamAnalysis, AI_ANALYSIS_INTERVAL_MS);
    triggerWebcamAnalysis();

    // Kiosk Mode: Enforce Lockdown
    await enforceLockdown();

    console.log('🖥️ Triggered screen snapshot capture for session:', sessionId);
    console.log('📸 Triggered webcam snapshot capture for session:', sessionId);

    // Anti-Cheat: Scan for Interview Coder / Cluely
    startCheatingToolDetection();

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
    // Add final browsing summary event to the queue
    const browsingSummary = browsingTracker.generateSummaryEvent();
    if (browsingSummary) logEvent(browsingSummary);
    browsingTracker.stop();

    // Perform a SINGLE final sync for all remaining events
    await syncEvents();

    // End session on backend (async, don't block UI summary)
    fetch(`${CONFIG.API_BASE}/sessions/${examSession.sessionId}/end`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    }).catch(error => console.warn('Backend session end failed:', error.message));

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
      nofaceCount: 0,
      multifaceCount: 0,
      phoneCount: 0,
      audioAnomalyCount: 0,
      lastScreenCapture: null,
      lastWebcamCapture: null,
      lastSync: null,
      globalRiskScore: 0,
      globalEffortScore: 100,
    };

    await chrome.storage.local.set({ examSession: null });

    // Stop periodic sync
    stopPeriodicSync();
    if (domCaptureIntervalId) {
      clearInterval(domCaptureIntervalId);
      domCaptureIntervalId = null;
    }
    if (webcamCaptureIntervalId) {
      clearInterval(webcamCaptureIntervalId);
      webcamCaptureIntervalId = null;
    }
    if (webcamAnalysisIntervalId) {
      clearInterval(webcamAnalysisIntervalId);
      webcamAnalysisIntervalId = null;
    }
    webcamUploadInFlight = false;

    // Notify all tabs
    notifyAllTabs('EXAM_STOPPED');

    // Close capture window
    if (captureWindowId) {
      chrome.windows.remove(captureWindowId).catch(() => { });
      captureWindowId = null;
    }

    chrome.notifications.create({
      type: 'basic',
      iconUrl: 'icons/icon48.png',
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
    const url = sanitizeUrl(tab.url);

    // Update browsing tracker with new active tab
    browsingTracker.trackSiteChange(activeInfo.tabId, tab.url, tab.title);

    // Log as TAB_SWITCH (not NAVIGATION) so the server counts it correctly
    logEvent({
      type: 'TAB_SWITCH',
      timestamp: Date.now(),
      data: {
        url: url,
        title: tab.title || 'Unknown',
        action: 'TAB_SWITCH',
        // Include browsing context
        currentCategory: browsingTracker.activeSite?.category || 'unknown',
        browsingRisk: browsingTracker.browsingRiskScore,
        effortScore: browsingTracker.effortScore,
      }
    });

    // Classify the URL and log risk event if matched
    const classification = classifyUrl(tab.url, tab.title);
    if (classification) {
      logEvent({
        type: 'FORBIDDEN_SITE',
        timestamp: Date.now(),
        data: {
          url: url,
          title: tab.title || 'Unknown',
          category: classification.category,
          site: classification.site,
          riskLevel: classification.riskLevel,
          timeOnSite: 0,
          message: `${classification.category} site detected: ${classification.site}`,
        }
      });

      // Send via WebSocket for immediate dashboard alert
      sendViaWebSocket({
        type: 'forbidden_site_detected',
        session_id: examSession.sessionId,
        category: classification.category,
        site: classification.site,
        url: url,
        browsingRisk: browsingTracker.browsingRiskScore,
        effortScore: browsingTracker.effortScore,
      });

      console.log(`🚨 [${classification.category}] Forbidden site: ${classification.site}`);
    }

    examSession.tabSwitchCount++;
    await saveSession();
  } catch (error) {
    console.warn('Tab monitoring error:', error.message);
  }
});

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (!examSession.active || !changeInfo.url) return;

  const url = sanitizeUrl(changeInfo.url);

  // Update browsing tracker when URL changes in any tab
  // Only track if this is the active tab
  if (tab.active) {
    browsingTracker.trackSiteChange(tabId, changeInfo.url, tab.title);
  } else {
    // Still record the visit even for background tabs
    const classification = classifyUrl(changeInfo.url, tab.title);
    const category = classification
      ? (classification.trackerCategory || classification.category || 'other').toLowerCase()
      : (isLocalExamPlatform(changeInfo.url) ? 'exam' : 'other');
    browsingTracker.recordVisit(changeInfo.url, tab.title, category,
                                classification?.riskLevel || 'none');
  }

  logEvent({
    type: 'NAVIGATION',
    timestamp: Date.now(),
    data: {
      url: url,
      title: tab.title || 'Unknown',
      action: 'NAVIGATE',
      isActiveTab: tab.active,
      currentCategory: browsingTracker.activeSite?.category || 'unknown',
    }
  });

  // Classify the URL and log risk event if matched
  const classification = classifyUrl(changeInfo.url);
  if (classification) {
    logEvent({
      type: 'FORBIDDEN_SITE',
      timestamp: Date.now(),
      data: {
        url: url,
        title: tab.title || 'Unknown',
        category: classification.category,
        site: classification.site,
        riskLevel: classification.riskLevel,
        isActiveTab: tab.active,
        message: `${classification.category} site detected: ${classification.site}`,
      }
    });

    sendViaWebSocket({
      type: 'forbidden_site_detected',
      session_id: examSession.sessionId,
      category: classification.category,
      site: classification.site,
      url: url,
      browsingRisk: browsingTracker.browsingRiskScore,
    });

    console.log(`🚨 [${classification.category}] Forbidden site: ${classification.site}`);
  }
});

// Track when a tab is created (student opening new tabs)
chrome.tabs.onCreated.addListener(async (tab) => {
  if (!examSession.active) return;
  
  logEvent({
    type: 'TAB_CREATED',
    timestamp: Date.now(),
    data: {
      tabId: tab.id,
      url: tab.pendingUrl || tab.url || 'about:blank',
      message: 'New tab opened during exam',
      openTabsCount: browsingTracker.openTabs.length + 1,
    }
  });
});

// Track when a tab is closed
chrome.tabs.onRemoved.addListener((tabId, removeInfo) => {
  if (!examSession.active) return;
  
  // Check if the closed tab was flagged
  const closedTab = browsingTracker.openTabs.find(t => t.tabId === tabId);
  
  logEvent({
    type: 'TAB_CLOSED',
    timestamp: Date.now(),
    data: {
      tabId,
      wasWindowClosing: removeInfo.isWindowClosing,
      wasFlagged: closedTab ? closedTab.riskLevel !== 'none' : false,
      closedCategory: closedTab?.category || 'unknown',
      message: 'Tab closed during exam',
    }
  });
  
  // Remove from open tabs
  browsingTracker.openTabs = browsingTracker.openTabs.filter(t => t.tabId !== tabId);
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

// Message listener moved to top for early registration

// ==================== EVENT LOGGING ====================

function logEvent(event) {
  event.sessionId = examSession.sessionId;
  event.id = `evt-${Date.now()}-${randomId()}`;

  examSession.events.push(event);

  // PREVENT MEMORY LEAK: If sync is failing, keep only the most recent 50 events
  if (examSession.events.length > 50) {
    examSession.events = examSession.events.slice(-50);
  }

  // Update specific counts
  const type = event.type;
  if (type === 'COPY' || type === 'PASTE' || type === 'CLIPBOARD_PASTE' || type === 'PASTE_DETECTED' || type === 'VELOCITY_VIOLATION') {
    examSession.copyCount++;
  } else if (type === 'TAB_SWITCH' || type === 'TAB_CREATED') {
    examSession.tabSwitchCount++;
  } else if (type === 'FACE_ABSENT' || type === 'FACE_ABSENT_VIOLATION') {
    examSession.nofaceCount++;
  } else if (type === 'MULTIPLE_FACES' || type === 'MULTIPLE_FACES_DETECTED') {
    examSession.multifaceCount++;
  } else if (type === 'PHONE_DETECTED') {
    examSession.phoneCount++;
  }

  // Trigger sync if queue is large
  if (examSession.events.length >= 20) {
    syncEvents();
  }

  // Send via WebSocket for immediate proctor update
  sendViaWebSocket(event);

  // V2: post client-side events to queue-based API (hybrid inference)
  if (examSession.active && examSession.sessionId) {
    const v2TypeMap = {
      TAB_SWITCH: 'tab_switch',
      TAB_CREATED: 'tab_switch',
      WINDOW_BLUR: 'window_blur',
      COPY: 'copy_paste',
      PASTE: 'copy_paste',
      CLIPBOARD_PASTE: 'copy_paste',
      PAGE_HIDDEN: 'page_hidden',
      VISIBILITY_CHANGE: 'page_hidden',
    };
    const v2Type = v2TypeMap[type];
    if (v2Type) {
      postV2Event(examSession.sessionId, v2Type, event.data || {});
    }
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
      // Clear synced events using highly efficient Set-based filtering (O(N))
      const syncedIds = new Set(eventsToSync.map(s => s.id));
      examSession.events = examSession.events.filter(e => !syncedIds.has(e.id));
      
      examSession.lastSync = Date.now();
      await saveSession();
      console.log(`☁️ Synced ${eventsToSync.length} events`);
    }
  } catch (error) {
    console.warn('⚠️ Sync failed:', error.message);
  }
}

/**
 * Fast live screen upload — no AI blocking, broadcasts immediately via WebSocket.
 */
function uploadLiveScreenFrame(image, url = 'screen-share') {
  if (!examSession.active || !examSession.sessionId || !image) return;

  fetch(`${CONFIG.API_BASE}/uploads/screenshot`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: examSession.sessionId,
      timestamp: Date.now(),
      image_data: image,
    }),
    keepalive: true,
  }).catch(() => {});
}

/**
 * Fast live webcam upload — no AI blocking, broadcasts immediately via WebSocket.
 */
function uploadLiveWebcamFrame(image) {
  if (!examSession.active || !examSession.sessionId || !image) return;

  fetch(`${CONFIG.API_BASE}/uploads/webcam`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: examSession.sessionId,
      timestamp: Date.now(),
      image_data: image,
    }),
    keepalive: true,
  }).catch(() => {});
}

/**
 * Upload high-fidelity snapshot for content analysis (native approach)
 */
async function uploadDOMSnapshot(data) {
    if (!examSession.active) return { success: false };

    console.log('📷 Uploading native tab snapshot for OCR content analysis...');
    try {
        const response = await fetch(`${CONFIG.API_BASE}/analysis/process`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: examSession.sessionId,
                timestamp: Date.now(),
                screen_image: data.image, // Use screen_image field so OCR service picks it up
                is_dom_capture: true,
                source_url: data.url
            }),
        });

        if (response.ok) {
            const result = await response.json();
            // If the OCR finds forbidden text on the specific page the student is viewing
            if (result.forbidden_detected) {
                logEvent({
                    type: 'VISUAL_FORBIDDEN_CONTENT',
                    timestamp: Date.now(),
                    data: { 
                        url: data.url, 
                        keywords: result.detected_keywords,
                        message: `Forbidden content detected visually on page: ${data.url}`
                    }
                });
            }
            return { success: true, analysis: result };
        }
    } catch (err) {
        console.warn('Tab snapshot upload failed:', err.message);
    }
    return { success: false };
}

function requestCaptureFrame(messageType) {
  return new Promise((resolve) => {
    getCaptureTabId()
      .then((tabId) => {
        chrome.tabs.sendMessage(tabId, { type: messageType }, (response) => {
          if (chrome.runtime.lastError) {
            resolve(null);
            return;
          }
          resolve(response?.image || null);
        });
      })
      .catch(() => resolve(null));
  });
}

function isInternalCaptureUrl(url = '') {
  return url.includes('capture-page') || url.startsWith('chrome-extension://') || url.startsWith('chrome://');
}

async function captureVisibleExamTab() {
  const focusedWindow = await chrome.windows.getLastFocused({ populate: true }).catch(() => null);
  const candidateTabs = [];

  if (focusedWindow?.tabs) {
    candidateTabs.push(...focusedWindow.tabs.filter((tab) => tab.active));
    candidateTabs.push(...focusedWindow.tabs.filter((tab) => !tab.active));
  }

  const allTabs = await chrome.tabs.query({});
  candidateTabs.push(...allTabs);

  const seenTabIds = new Set();
  for (const tab of candidateTabs) {
    if (!tab?.id || seenTabIds.has(tab.id)) continue;
    seenTabIds.add(tab.id);

    const tabUrl = tab.url || '';
    if (!tabUrl || isInternalCaptureUrl(tabUrl)) continue;

    try {
      const image = await chrome.tabs.captureVisibleTab(tab.windowId, { format: 'jpeg', quality: 30 });
      if (image) {
        return { image, url: tabUrl };
      }
    } catch {
      // Try the next visible tab.
    }
  }

  return null;
}

async function triggerNativeDOMCapture() {
  if (!examSession.active) return;

  const screenImage = await requestCaptureFrame('CAPTURE_SCREEN_FRAME');
  if (screenImage) {
    uploadLiveScreenFrame(screenImage, 'screen-share');
    return;
  }

  const visibleTabCapture = await captureVisibleExamTab();
  if (visibleTabCapture?.image) {
    uploadLiveScreenFrame(visibleTabCapture.image, visibleTabCapture.url);
  }
}

/**
 * Trigger a webcam snapshot from the capture window
 */
async function triggerWebcamCapture() {
  if (!examSession.active || !captureWindowId) return;

  try {
    const webcamImage = await requestCaptureFrame('CAPTURE_WEBCAM_FRAME');
    if (webcamImage) {
      uploadLiveWebcamFrame(webcamImage);
    }
  } catch (err) {
    console.warn('Webcam capture trigger failed:', err.message);
  }
}

/**
 * Periodic AI analysis on webcam frames (slower, does not block live streaming).
 */
async function triggerWebcamAnalysis() {
  if (!examSession.active || !captureWindowId || webcamUploadInFlight) return;

  try {
    const webcamImage = await requestCaptureFrame('CAPTURE_WEBCAM_FRAME');
    if (webcamImage) {
      await uploadWebcamFrame(webcamImage);
    }
  } catch (err) {
    console.warn('Webcam analysis trigger failed:', err.message);
  }
}

/**
 * Upload webcam frame for AI vision analysis (Face/Gaze/Phone)
 */
async function uploadWebcamFrame(image) {
  if (!examSession.active || webcamUploadInFlight) return;

  webcamUploadInFlight = true;
    
    try {
        const response = await fetch(`${CONFIG.API_BASE}/analysis/process`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: examSession.sessionId,
                timestamp: Date.now(),
                webcam_image: image,
                is_dom_capture: false
            })
        });

        if (response.ok) {
            const result = await response.json();
            // Process AI feedback on-the-fly (dashboard also gets this via WS)
            if (result.phone_detected) {
                logEvent({
                    type: 'PHONE_DETECTED',
                    timestamp: Date.now(),
                    data: { message: 'Cell phone detected in your webcam feed!' }
                });
            }
            if (result.face_detected === false) {
                 examSession.nofaceCount++;
            }
            examSession.lastWebcamCapture = Date.now();
        }
    } catch (err) {
        console.warn('Webcam AI upload failed:', err.message);
      } finally {
        webcamUploadInFlight = false;
    }
}

async function getCaptureTabId() {
    if (!captureWindowId) throw new Error('No capture window');
    const tabs = await chrome.tabs.query({ windowId: captureWindowId });
    if (!tabs || tabs.length === 0) throw new Error('No tabs in capture window');
    return tabs[0].id;
}

// Close all Chrome windows when phone is detected
async function closeAllChromeWindows() {
  try {
    const windows = await chrome.windows.getAll();
    for (const window of windows) {
      await chrome.windows.remove(window.id).catch(() => { });
    }
    console.log('🔇 All Chrome windows closed due to critical violation');
  } catch (error) {
    console.error('Failed to close windows:', error);
  }
}

// ==================== PERIODIC SYNC ====================

function startPeriodicSync() {
  if (syncIntervalId) return;

  // Frequent event sync to keep DB updated
  syncIntervalId = setInterval(() => {
    if (examSession.active) {
      pushSessionScores(true);
      if (examSession.events.length > 0) {
        syncEvents();
      }
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

async function isBackendReachable() {
  try {
    const response = await fetch(`${BACKEND_URL}/ws/stats`, {
      method: 'GET',
      cache: 'no-store',
    });
    return response.ok;
  } catch {
    return false;
  }
}

function connectWebSocket() {
  if (!examSession.active || !examSession.sessionId) return;

  if (
    wsConnection &&
    (wsConnection.readyState === WebSocket.OPEN ||
      wsConnection.readyState === WebSocket.CONNECTING)
  ) {
    return;
  }
  if (wsConnecting) return;

  wsConnecting = true;

  isBackendReachable()
    .then((reachable) => {
      wsConnecting = false;
      if (!examSession.active) return;

      if (!reachable) {
        console.warn(`🔌 Backend unreachable at ${BACKEND_URL}, retrying WebSocket in ${wsReconnectDelayMs}ms`);
        if (wsReconnectTimer) clearTimeout(wsReconnectTimer);
        wsReconnectTimer = setTimeout(connectWebSocket, wsReconnectDelayMs);
        wsReconnectDelayMs = Math.min(wsReconnectDelayMs * 2, 30000);
        return;
      }

      wsReconnectDelayMs = 3000;

      const studentId = examSession.studentId || examSession.sessionId || 'unknown';
      const wsUrl = `${CONFIG.WS_URL}/${encodeURIComponent(studentId)}?session_id=${encodeURIComponent(examSession.sessionId)}`;

      try {
        wsConnection = new WebSocket(wsUrl);

        wsConnection.onopen = () => {
          console.log('🔌 WebSocket connected to backend');
          wsReconnectDelayMs = 3000;
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
          if (examSession.active) {
            if (wsReconnectTimer) clearTimeout(wsReconnectTimer);
            wsReconnectTimer = setTimeout(connectWebSocket, wsReconnectDelayMs);
          }
        };

        wsConnection.onerror = () => {
          // onclose handles reconnect; avoid noisy duplicate logs
        };
      } catch (e) {
        console.warn('🔌 WebSocket connection failed:', e.message || e);
        wsConnection = null;
        if (examSession.active) {
          if (wsReconnectTimer) clearTimeout(wsReconnectTimer);
          wsReconnectTimer = setTimeout(connectWebSocket, wsReconnectDelayMs);
        }
      }
    })
    .catch(() => {
      wsConnecting = false;
    });
}

function disconnectWebSocket() {
  if (wsReconnectTimer) {
    clearTimeout(wsReconnectTimer);
    wsReconnectTimer = null;
  }
  wsConnecting = false;
  wsReconnectDelayMs = 3000;
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
        iconUrl: 'icons/icon48.png',
        title: '⚠️ Proctor Alert',
        message: data.data?.message || 'Please focus on your exam.',
        priority: 2,
      });
      notifyAllTabs('PROCTOR_ALERT');
      break;

    case 'risk_score_update':
      // Handle both formats: {data: {risk_score}} or {risk_score} directly
      const riskData = data.data || data;
      console.log(`📊 Risk score updated: ${riskData.risk_score}`);
      if (examSession.active && riskData) {
        examSession.globalRiskScore = riskData.risk_score || 0;
        examSession.globalEffortScore = riskData.effort_alignment || riskData.engagement_score || 100;
      }
      break;

    case 'anomaly_alert':
      const anomalyType = (data.data?.type || data.alert_type || '').toUpperCase();
      if (anomalyType.includes('MULTIPLE_FACES') || anomalyType.includes('MULTI_FACE')) {
        examSession.multifaceCount++;
      } else if (anomalyType.includes('AUDIO_ANOMALY')) {
        examSession.audioAnomalyCount++;
      } else if (anomalyType.includes('FACE_ABSENT') || anomalyType.includes('FACE_NOT_FOUND')) {
        examSession.nofaceCount++;
      } else if (anomalyType.includes('PHONE_DETECTED')) {
        logEvent({
          type: 'PHONE_DETECTED',
          timestamp: Date.now(),
          data: { message: 'Cell phone detected in your webcam feed!' }
        });
      }
      
      chrome.notifications.create({
        type: 'basic',
        iconUrl: 'icons/icon48.png',
        title: '⚠️ AI Analysis Alert',
        message: data.data?.message || data.message || 'Suspicious activity detected.',
        priority: 2,
      });
      saveSession();
      break;

    case 'vision_alert':
      // Handler for alerts from the live stream analysis (direct from vision engine)
      if (data.violations && Array.isArray(data.violations)) {
        data.violations.forEach(v => {
          const uv = v.toUpperCase();
          if (uv.includes('MULTIPLE_FACES')) examSession.multifaceCount++;
          if (uv.includes('FACE_ABSENT') || uv.includes('FACE_NOT_FOUND')) examSession.nofaceCount++;
          if (uv.includes('PHONE_DETECTED')) {
            logEvent({
              type: 'PHONE_DETECTED',
              timestamp: Date.now(),
              data: { message: 'Cell phone detected in live stream!' }
            });
          }
        });
        saveSession();
      }
      break;

    case 'force_end':
      // Proctor forced session end
      stopExamSession();
      break;

    case 'debug_trigger_shutdown':
      // DEBUG: Allow manual trigger for testing
      processViolation('PHONE_DETECTED', { message: 'Manual debug trigger' });
      break;

    default:
      break;
  }
}

/**
 * Common handler for critical violations that require shutdown
 */
async function processViolation(type, data) {
  if (!examSession.active) return;

  console.log(`🚨 [${type}] Violation! Initiating shutdown...`);
  
  logEvent({
    type: type,
    timestamp: Date.now(),
    data: data,
  });

  // Show warning notification
  chrome.notifications.create({
    type: 'basic',
    iconUrl: 'icons/icon48.png',
    title: '🚨 EXAM VIOLATION DETECTED',
    message: `${data.message || 'Serious violation detected.'} Chrome will close in 3 seconds.`,
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
}

// Send event via WebSocket for immediate dashboard update
function sendViaWebSocket(eventData) {
  if (wsConnection && wsConnection.readyState === WebSocket.OPEN) {
    wsConnection.send(`event:${JSON.stringify(eventData)}`);
    return true;
  }
  return false;
}

async function analyzePageContext(pageContext) {
  if (!examSession.active) {
    return { success: false, reason: 'session_inactive' };
  }

  const domain = pageContext.domain || (() => {
    try {
      return new URL(pageContext.url || '').hostname.replace(/^www\./, '').toLowerCase();
    } catch {
      return '';
    }
  })();

  const path = pageContext.path || (() => {
    try {
      return new URL(pageContext.url || '').pathname || '';
    } catch {
      return '';
    }
  })();

  const payload = {
    session_id: examSession.sessionId,
    student_id: examSession.studentId || examSession.sessionId || '',
    url: pageContext.url || '',
    domain,
    path,
    title: pageContext.title || '',
    content: pageContext.content || '',
    clipboard_text: pageContext.clipboard_text || '',
    youtube_title: pageContext.youtube_title || '',
    youtube_channel: pageContext.youtube_channel || '',
    exam_subject: examSession.examId || pageContext.exam_subject || '',
    referrer: pageContext.referrer || '',
    tab_duration_seconds: pageContext.tab_duration_seconds || 0,
    tab_switch_count: examSession.tabSwitchCount || 0,
    copy_count: examSession.copyCount || 0,
    paste_count: pageContext.paste_count || 0,
    focus_lost_count: pageContext.focus_lost_count || 0,
    hidden_count: pageContext.hidden_count || 0,
    recent_domains: Array.isArray(pageContext.recent_domains) ? pageContext.recent_domains : [],
    page_context: pageContext,
    signals: {
      ...(pageContext.signals || {}),
      source: 'content_agent_patch',
      session_active: examSession.active,
    },
  };

  try {
    const response = await fetch(`${CONFIG.API_BASE}/v2/analyze-site`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.warn('🧠 v2 analysis failed:', response.status, errorText.slice(0, 120));
      return { success: false, error: errorText };
    }

    const verdict = await response.json();
    const broadcast = {
      type: 'SITE_VERDICT',
      ...verdict,
      session_id: verdict.session_id || payload.session_id,
      student_id: verdict.student_id || payload.student_id,
      generated_at: verdict.generated_at || new Date().toISOString(),
      page_context: pageContext,
    };

    sendViaWebSocket(broadcast);
    await chrome.storage.local.set({ lastSiteVerdict: broadcast }).catch(() => {});

    // Update browsing scores from full page content analysis
    const modelClassification = await classifyPageWithModel({
      url: pageContext.url,
      title: pageContext.title,
      content: pageContext.content,
      signals: pageContext.signals || {},
    });
    if (modelClassification) {
      browsingTracker.applyModelClassification(pageContext.url, modelClassification);
    }

    return { success: true, verdict: broadcast };
  } catch (error) {
    console.warn('🧠 v2 analysis error:', error.message);
    return { success: false, error: error.message };
  }
}

// ==================== TRANSFORMER ANALYSIS ====================

async function analyzeTextWithTransformer(text) {
  if (!text || text.length < 10) return { success: false, reason: 'text_too_short' };

  try {
    const response = await fetch(`${CONFIG.API_BASE}/transformer/similarity`, {
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

async function enforceLockdown() {
  try {
    const windows = await chrome.windows.getAll({ windowTypes: ['normal', 'popup'] });

    // Fullscreen the student's exam window — not the capture popup
    const examWindow = windows.find(
      (window) => window.id !== captureWindowId && window.type === 'normal'
    );

    if (examWindow?.id) {
      await chrome.windows.update(examWindow.id, {
        state: 'fullscreen',
        focused: true,
      }).catch(async () => {
        await chrome.windows.update(examWindow.id, {
          state: 'maximized',
          focused: true,
        }).catch(() => {});
      });
    }

    logEvent({
      type: 'KIOSK_MODE_ENFORCED',
      timestamp: Date.now(),
      data: { message: 'Exam window fullscreen enforced.' },
    });

    const fingerprint = await getDeviceFingerprint();
    examSession.deviceFingerprint = fingerprint;
  } catch (err) {
    console.warn('Lockdown skipped:', err?.message || err);
  }
}

async function getDeviceFingerprint() {
  let displayLabel = 'unknown-display';

  try {
    if (chrome.system?.display?.getInfo) {
      const displayInfo = await new Promise((resolve) => {
        chrome.system.display.getInfo(resolve);
      });
      const bounds = displayInfo?.[0]?.bounds || { width: 0, height: 0 };
      displayLabel = `${bounds.width}x${bounds.height}-${displayInfo?.length || 0}`;
    }
  } catch {
    // Optional permission or API unavailable
  }

  const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
  return btoa(`${displayLabel}-${navigator.userAgent}-${timezone}`);
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
      const response = await fetch(`${CONFIG.API_BASE}/transformer/cross-compare`, {
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

// ==================== CHEATING TOOL DETECTION ====================
// Detects Interview Coder / Cluely / Free-Cluely and similar AI overlay tools

let cheatingDetectionInterval = null;
let lastCheatingReportAt = 0;
let lastCheatingReportKey = '';
const CHEAT_REPORT_COOLDOWN_MS = 5 * 60 * 1000;

const CHEATING_TOOL_SIGNATURES = {
  // Known cheating tool window title patterns (specific tool names only)
  titlePatterns: [
    'interview coder',
    'interviewcoder',
    'cluely',
    'free-cluely',
    'free cluely',
  ],

  // Known cheating tool URLs (exclude dev ports used by ExamGuard/Vite)
  urlPatterns: [
    'cluely.com',
    'interviewcoder.co',
    'free-cluely',
  ],
};

const EXAMGUARD_ALLOWED_TAB_PATTERNS = [
  'localhost:3000',
  '127.0.0.1:3000',
  'localhost:8000',
  '127.0.0.1:8000',
  'examguard',
  'capture-page.html',
  'chrome-extension://',
];

function isAllowedExamTab(tab) {
  const url = (tab.url || '').toLowerCase();
  if (!url || url.startsWith('chrome://') || url.startsWith('chrome-extension://')) {
    return true;
  }
  return EXAMGUARD_ALLOWED_TAB_PATTERNS.some((pattern) => url.includes(pattern));
}

function startCheatingToolDetection() {
  if (cheatingDetectionInterval) clearInterval(cheatingDetectionInterval);

  // Run immediately, then every 15 seconds
  scanForCheatingTools();
  cheatingDetectionInterval = setInterval(scanForCheatingTools, 15000);

  console.log('🔍 Anti-cheat: Cheating tool detection started');
}

function stopCheatingToolDetection() {
  if (cheatingDetectionInterval) {
    clearInterval(cheatingDetectionInterval);
    cheatingDetectionInterval = null;
  }
}

async function scanForCheatingTools() {
  if (!examSession.active) return;

  const detections = [];

  // Tab title/URL scan — skip ExamGuard dashboard, backend, and extension pages
  try {
    const tabs = await chrome.tabs.query({});
    for (const tab of tabs) {
      if (isAllowedExamTab(tab)) continue;

      const title = (tab.title || '').toLowerCase();
      const url = (tab.url || '').toLowerCase();

      for (const pattern of CHEATING_TOOL_SIGNATURES.titlePatterns) {
        if (title.includes(pattern)) {
          detections.push({
            method: 'title_match',
            pattern,
            tabId: tab.id,
            title: tab.title,
            url: tab.url,
            message: `Cheating tool window detected: "${tab.title}"`,
          });
          break;
        }
      }

      for (const pattern of CHEATING_TOOL_SIGNATURES.urlPatterns) {
        if (url.includes(pattern)) {
          detections.push({
            method: 'url_match',
            pattern,
            tabId: tab.id,
            url: tab.url,
            message: `Cheating tool URL detected: ${tab.url}`,
          });
          break;
        }
      }
    }
  } catch (err) {
    console.warn('Tab scan error:', err);
  }

  if (detections.length === 0) return;

  const reportKey = detections
    .map((d) => `${d.method}:${d.pattern || d.url || d.title || ''}`)
    .sort()
    .join('|');
  const now = Date.now();
  if (reportKey === lastCheatingReportKey && now - lastCheatingReportAt < CHEAT_REPORT_COOLDOWN_MS) {
    return;
  }
  lastCheatingReportKey = reportKey;
  lastCheatingReportAt = now;

  // Report detections
  if (detections.length > 0) {
    console.warn('🚨 CHEATING TOOL DETECTED:', detections);

    for (const detection of detections) {
      logEvent({
        type: 'CHEATING_TOOL_DETECTED',
        timestamp: Date.now(),
        data: {
          ...detection,
          severity: 'CRITICAL',
          tool_type: detection.method === 'port_scan' ? 'AI_OVERLAY_APP' : 'CHEATING_SOFTWARE',
        }
      });
    }

    // Send critical alert via WebSocket
    sendViaWebSocket({
      type: 'cheating_tool_alert',
      session_id: examSession.sessionId,
      detections: detections.map(d => ({
        method: d.method,
        message: d.message,
        port: d.port,
        url: d.url,
      })),
      severity: 'CRITICAL',
      timestamp: Date.now(),
    });

    // Upload critical event to backend
    try {
      await fetch(`${CONFIG.API_BASE}/events/log`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: examSession.sessionId,
          event_type: 'CHEATING_TOOL_DETECTED',
          risk_level: 'critical',
          data: {
            detections: detections.length,
            details: detections,
            message: `⚠️ CRITICAL: ${detections.length} cheating tool signature(s) detected`,
          },
          timestamp: new Date().toISOString(),
        }),
      });
    } catch (err) {
      console.warn('Failed to report cheating tool detection:', err);
    }

    // Show notification to student (deterrent)
    chrome.notifications.create(`cheat-detect-${Date.now()}`, {
      type: 'basic',
      iconUrl: 'icons/icon48.png',
      title: '⚠️ ExamGuard Pro - Security Alert',
      message: 'Unauthorized software detected. This has been reported to your proctor. Please close all cheating tools immediately.',
      priority: 2,
      requireInteraction: true,
    });
  }
}
