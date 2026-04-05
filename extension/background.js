/**
 * ExamGuard Pro - Background Service Worker v2.0
 * Enhanced session management, robust error handling, and retry logic
 */

// ==================== CONFIGURATION ====================
// Change BACKEND_URL to your deployed server URL
// For local dev: 'http://localhost:8000'
// For cloud:     'https://exam-security.onrender.com'
const BACKEND_URL = 'http://127.0.0.1:8000';

const CONFIG = {
  API_BASE: `${BACKEND_URL}/api`,
  WS_URL: `${BACKEND_URL.replace('http://', 'ws://').replace('https://', 'wss://')}/ws/student`,
  SYNC_INTERVAL: 5000,          // Sync events every 5s
  TRANSFORMER_INTERVAL: 15000,  // Run transformer analysis every 15s
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
let clipboardTexts = [];     // Buffer for transformer analysis
let pendingAnalysis = [];    // Buffer for pending text analysis
let domCaptureIntervalId = null;
let webcamCaptureIntervalId = null; 
let webcamUploadInFlight = false;

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

    case 'GET_STATUS':
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
        globalRiskScore: examSession.globalRiskScore || 0,
        globalEffortScore: examSession.globalEffortScore || 100,
        browsing: examSession.active ? browsingTracker.getStats() : null,
      });
      return true;


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
const browsingTracker = {
  // Current active site tracking
  activeSite: null,            // { url, title, tabId, category, startTime }
  
  // Time spent per category (milliseconds)
  timeByCategory: {
    exam: 0,
    learning: 0,
    ai: 0,
    cheating: 0,
    entertainment: 0,
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
  
  /** Start tracking when exam begins */
  start() {
    this.reset();
    // Run an initial tab audit
    this.auditOpenTabs();
    // Audit open tabs every 10 seconds
    this.auditIntervalId = setInterval(() => this.auditOpenTabs(), 10000);
  },
  
  /** Stop tracking when exam ends */
  stop() {
    // Flush the active site time
    this.flushActiveSite();
    if (this.auditIntervalId) {
      clearInterval(this.auditIntervalId);
      this.auditIntervalId = null;
    }
  },
  
  /** Reset all tracking data */
  reset() {
    this.activeSite = null;
    this.timeByCategory = { exam: 0, learning: 0, ai: 0, cheating: 0, entertainment: 0, other: 0 };
    this.visitedSites = [];
    this.openTabs = [];
    this.browsingRiskScore = 0;
    this.effortScore = 100;
  },
  
  /** Called when user switches to a new tab or navigates to a new URL */
  trackSiteChange(tabId, url, title) {
    // Flush time for the previous active site
    this.flushActiveSite();
    
    // Classify the new URL
    const classification = classifyUrl(url);
    let category = 'other';
    let riskLevel = 'none';
    if (classification) {
      category = classification.category.toLowerCase(); // ai, cheating, entertainment
      riskLevel = classification.riskLevel;
    } else if (this.isExamRelated(url)) {
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
  },

  /** Track visual presence (from html2canvas) */
  trackVisualEngagement(data) {
    if (!this.activeSite) return;
    
    // Check if what was captured is actually the exam page
    const isActuallyExam = this.isExamRelated(data.url);
    if (isActuallyExam) {
        // Boost effort if student is visually focused on the exam
        this.effortScore = Math.min(100, this.effortScore + 5);
        console.log('📈 Visual focus on exam page confirmed');
    } else {
        // Flag non-exam visual content
        const classification = classifyUrl(data.url);
        if (classification && classification.riskLevel !== 'none') {
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
  
  /** Check if a URL is productive (exam platform itself, LMS, or learning research) */
  isExamRelated(url) {
    if (!url) return false;
    try {
      const hostname = new URL(url).hostname.toLowerCase();
      // Common LMS / exam platforms
      const examPlatforms = [
        'localhost', '127.0.0.1',             // Local exam platform
        'onrender.com',                       // Cloud backend
        'canvas.', 'blackboard.', 'moodle.',  // LMS platforms
        'forms.google.com', 'docs.google.com',
        'exam.', 'test.', 'quiz.', 'assessment.',
        'gradescope.com', 'proctorio.com',
      ];
      if (examPlatforms.some(p => hostname.includes(p))) return true;
      
      const fullUrl = url.toLowerCase();
      // Also count learning/research as productive time (increases effort score)
      if (typeof LEARNING_SITES !== 'undefined' && LEARNING_SITES.some(p => hostname.includes(p) || fullUrl.includes(p))) {
        return true;
      }
      return false;
    } catch {
      return false;
    }
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
        
        const classification = classifyUrl(tab.url);
        const entry = {
          tabId: tab.id,
          url: sanitizeUrl(tab.url),
          title: tab.title || 'Unknown',
          category: classification ? classification.category : (this.isExamRelated(tab.url) ? 'EXAM' : 'OTHER'),
          riskLevel: classification ? classification.riskLevel : 'none',
          active: tab.active,
          pinned: tab.pinned,
        };
        
        auditResults.push(entry);
        if (classification) flaggedCount++;
        
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
    const otherTimeRatio = this.timeByCategory.other / totalTime;
    
    risk += aiTimeRatio * 50;              // AI usage: up to 50 risk (Semi-risk)
    risk += cheatingTimeRatio * 100;       // Cheating: up to 100 risk
    risk += entertainmentTimeRatio * 100;  // Entertainment: up to 100 risk (Max Risk)
    risk += otherTimeRatio * 40;           // Unclassified sites: up to 40 risk (Distraction)
    
    // Count-based risk (unique flagged sites)
    const flaggedSites = this.visitedSites.filter(s => ['ai', 'cheating', 'entertainment'].includes(s.category));
    risk += Math.min(flaggedSites.length * 15, 60); 
    
    // Open tabs risk bonus
    const flaggedOpenTabs = this.openTabs.filter(t => t.riskLevel !== 'none').length;
    risk += Math.min(flaggedOpenTabs * 10, 40);
    
    this.browsingRiskScore = Math.min(Math.round(risk), 100);
    
    // --- Effort Score (0-100) ---
    // If student spends 100% on exam + learning => effort 100. If 0% => effort 0.
    const productiveTime = this.timeByCategory.exam + (this.timeByCategory.learning || 0);
    const productiveRatio = productiveTime / totalTime;
    const distractionTime = this.timeByCategory.ai + this.timeByCategory.cheating + this.timeByCategory.entertainment + this.timeByCategory.other;
    const distractionRatio = distractionTime / totalTime;
    
    // Base effort: strictly productive time (exam + learning) drives it up
    let effort = productiveRatio * 100;
    
    // Unclassified sites (other) do NOT give effort anymore, they act as distractions
    // Ratio Bonus: only if productive ratio is dominant (>70%)
    if (productiveRatio > 0.7) {
        effort += 20; 
    } else if (productiveRatio < 0.3) {
        effort -= 20; // Massive penalty for lack of focus
    }
    
    this.effortScore = Math.min(Math.max(Math.round(effort), 0), 100);
  },
  
  /** Generate a browsing summary event for syncing to server */
  generateSummaryEvent() {
    this.flushActiveSite();
    this.calculateScores();
    
    const totalTime = Object.values(this.timeByCategory).reduce((a, b) => a + b, 0);
    
    return {
      type: 'BROWSING_SUMMARY',
      timestamp: Date.now(),
      data: {
        timeByCategory: { ...this.timeByCategory },
        totalTime,
        browsingRiskScore: this.browsingRiskScore,
        effortScore: this.effortScore,
        uniqueSitesVisited: this.visitedSites.length,
        flaggedSitesCount: this.visitedSites.filter(s => ['ai', 'cheating', 'entertainment'].includes(s.category)).length,
        openTabsCount: this.openTabs.length,
        flaggedOpenTabs: this.openTabs.filter(t => t.riskLevel !== 'none').length,
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
        examTimePercent: totalTime > 0 ? Math.round(((this.timeByCategory.exam + (this.timeByCategory.learning || 0)) / totalTime) * 100) : 0,
        distractionTimePercent: totalTime > 0 ? Math.round(
          ((this.timeByCategory.ai + this.timeByCategory.cheating + this.timeByCategory.entertainment) / totalTime) * 100
        ) : 0,
      },
    };
  },
  
  /** Get current stats for the popup */
  getStats() {
    this.flushActiveSite();
    this.calculateScores();
    
    const totalTime = Object.values(this.timeByCategory).reduce((a, b) => a + b, 0);
    return {
      activeSite: this.activeSite ? {
        url: this.activeSite.url,
        category: this.activeSite.category,
        riskLevel: this.activeSite.riskLevel,
      } : null,
      timeByCategory: { ...this.timeByCategory },
      totalTime,
      browsingRiskScore: this.browsingRiskScore,
      effortScore: this.effortScore,
      flaggedSitesCount: this.visitedSites.filter(s => ['ai', 'cheating', 'entertainment'].includes(s.category)).length,
      totalSitesVisited: this.visitedSites.length,
      openTabsCount: this.openTabs.length,
      flaggedOpenTabs: this.openTabs.filter(t => t.riskLevel !== 'none').length,
      currentCategory: this.activeSite?.category || 'none',
    };
  },
};

// ==================== URL CLASSIFICATION ====================
// AI / LLM Sites - semi-effort, semi-risk
const AI_SITES = [
  'chat.openai.com', 'chatgpt.com', 'openai.com',
  'gemini.google.com', 'bard.google.com',
  'claude.ai', 'anthropic.com',
  'perplexity.ai', 'copilot.microsoft.com', 'bing.com/chat',
  'poe.com', 'character.ai', 'huggingface.co/chat', 'deepseek.com',
  'you.com', 'phind.com', 'writesonic.com', 'jasper.ai',
  'wolframalpha.com', 'symbolab.com', 'photomath.com', 'mathway.com',
];

// Entertainment / Distraction Sites - maximum risk (Critical)
const ENTERTAINMENT_SITES = [
  'youtube.com', 'netflix.com', 'hulu.com',
  'disneyplus.com', 'primevideo.com', 'amazon.com/gp/video',
  'twitch.tv', 'kick.com',
  'tiktok.com', 'instagram.com', 'facebook.com', 'twitter.com', 'x.com',
  'reddit.com', 'tumblr.com', 'pinterest.com',
  'snapchat.com', 'discord.com',
  'spotify.com', 'music.youtube.com', 'soundcloud.com',
  'store.steampowered.com', 'epicgames.com',
  'crunchyroll.com', 'funimation.com',
  'roblox.com', 'miniclip.com',
  // Streaming / movie sites
  'movhub.ws', 'movhub.to', 'fmovies.to', 'fmovies.wtf',
  'soap2day.to', 'soap2day.ac', 'putlocker.', 'gomovies.',
  'solarmovie.', '123movies.', 'yesmovies.', 'flixhq.to',
  'bflixz.to', 'myflixer.', 'cineb.net', 'hdtoday.',
  'tinyzone.', 'zoechip.', 'primewire.', 'movieorca.',
  'imdb.com', 'rottentomatoes.com', 'letterboxd.com',
  'vimeo.com', 'dailymotion.com',
  // Gaming
  'twitch.tv', 'poki.com', 'crazygames.com', 'kongregate.com',
  'itch.io', 'armor games.com', 'addictinggames.com',
  // Social / news / forums
  'threads.net', 'mastodon.social', 'linkedin.com',
  'buzzfeed.com', '9gag.com', 'imgur.com',
  'whatsapp.com', 'web.telegram.org', 'messenger.com',
  'cinehd.cc', 'cinehd.to', 'cinehd.ws'
];

// Cheating / Academic dishonesty sites - Critical risk
const CHEATING_SITES = [
  'chegg.com', 'coursehero.com', 'studocu.com',
  'quizlet.com', 'brainly.com', 'bartleby.com',
  'numerade.com', 'slader.com', 'litanswers.org',
  'pastebin.com',
];

// Learning / Project / Course sites - Max Effort
const LEARNING_SITES = [
  'udemy.com', 'coursera.org', 'edx.org', 'pluralsight.com', 'codecademy.com',
  'freecodecamp.org', 'khanacademy.org', 'udacity.com', 'skillshare.com',
  'datacamp.com', 'linkedin.com/learning',
  'stackoverflow.com', 'stackexchange.com', 'github.com', 'gitlab.com',
  'developer.', 'docs.', 'w3schools.com', 'mdn.io', 'geeksforgeeks.org',
  'google.com/search', 'google.co.in/search', 'bing.com/search', 'duckduckgo.com'
];

/** Classify a URL into a risk category */
function classifyUrl(url) {
  if (!url) return null;
  try {
    const hostname = new URL(url).hostname.replace(/^www\./, '');
    const fullUrl = url.toLowerCase();

    for (const site of LEARNING_SITES) {
      if (hostname.includes(site) || fullUrl.includes(site)) {
        return { category: 'LEARNING', site, riskLevel: 'none' };
      }
    }
    // Check AI after learning so that Claude/GPT count as LEARNING instead of AI if specified
    for (const site of AI_SITES) {
      if (hostname.includes(site) || fullUrl.includes(site)) {
        return { category: 'AI', site, riskLevel: 'medium' };
      }
    }
    for (const site of CHEATING_SITES) {
      if (hostname.includes(site) || fullUrl.includes(site)) {
        return { category: 'CHEATING', site, riskLevel: 'critical' };
      }
    }
    for (const site of ENTERTAINMENT_SITES) {
      if (hostname.includes(site) || fullUrl.includes(site)) {
        return { category: 'ENTERTAINMENT', site, riskLevel: 'critical' };
      }
    }
    return null;
  } catch {
    return null;
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
    // Minimize capture window to keep streams alive
    if (captureWindowId) {
      chrome.windows.update(captureWindowId, { state: 'minimized' }).catch(() => { });
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
    startPeriodicSync();

    if (webcamCaptureIntervalId) {
      clearInterval(webcamCaptureIntervalId);
      webcamCaptureIntervalId = null;
    }
    webcamUploadInFlight = false;
    triggerWebcamCapture();
    webcamCaptureIntervalId = setInterval(triggerWebcamCapture, 2500);

    // Kiosk Mode: Enforce Lockdown
    await enforceLockdown();

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
    const classification = classifyUrl(tab.url);
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
    const classification = classifyUrl(changeInfo.url);
    const category = classification ? classification.category.toLowerCase() : 
                     (browsingTracker.isExamRelated(changeInfo.url) ? 'exam' : 'other');
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

async function triggerNativeDOMCapture() {
  if (!examSession.active) return;
  
  try {
      const activeWindow = await chrome.windows.getCurrent();
      const tabs = await chrome.tabs.query({ active: true, windowId: activeWindow.id });
      if (!tabs || tabs.length === 0) return;
      
      const activeTab = tabs[0];
      
      // Fast, native native visual capture of the tab as JPEG
      // Scale down image quality and format to minimize transmission size
      const dataUrl = await chrome.tabs.captureVisibleTab(activeWindow.id, { format: 'jpeg', quality: 40 });
      
      if (dataUrl) {
          uploadDOMSnapshot({
              image: dataUrl,
              url: activeTab.url,
          }).catch(console.warn);
      }
  } catch (error) {
      // It's normal for this to fail if the browser doesn't have focus or is minimized
      console.warn('Native DOM capture failed:', error.message);
  }
}

/**
 * Trigger a webcam snapshot from the capture window
 */
async function triggerWebcamCapture() {
  if (!examSession.active || !captureWindowId || webcamUploadInFlight) return;

    try {
        // Since background script doesn't have the media stream, 
        // it must ask the capture window to grab a frame.
        chrome.tabs.sendMessage(await getCaptureTabId(), { type: 'CAPTURE_WEBCAM_FRAME' }, (response) => {
            if (response && response.image) {
                uploadWebcamFrame(response.image);
            }
        });
    } catch (err) {
        console.warn('Webcam capture trigger failed:', err.message);
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
    if (examSession.active && examSession.events.length > 0) {
      syncEvents();
    }
    // Send a browsing summary every sync cycle
    if (examSession.active) {
      const summary = browsingTracker.generateSummaryEvent();
      logEvent(summary);
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
    // 1. Get all windows
    const windows = await chrome.windows.getAll();
    // Use captureWindowId as the primary, fallback to active window
    const keepId = captureWindowId || (await chrome.windows.getCurrent()).id;

    // 2. Close all other windows (Extreme Kiosk Mode) - DISABLED for better UX
    /*
    for (const w of windows) {
      if (w.id !== keepId) {
        await chrome.windows.remove(w.id).catch(() => {});
      }
    }
    */

    // 3. Force Fullscreen and Focus
    await chrome.windows.update(keepId, {
      state: 'fullscreen',
      focused: true,
    });

    logEvent({
      type: 'KIOSK_MODE_ENFORCED',
      timestamp: Date.now(),
      data: { message: 'Kiosk mode active: other windows closed, fullscreen forced.' }
    });

    // 4. Device Binding
    const fingerprint = await getDeviceFingerprint();
    examSession.deviceFingerprint = fingerprint;

  } catch (err) {
    console.error('Failed to enforce lockdown:', err);
  }
}

async function getDeviceFingerprint() {
  const displayInfo = await new Promise(r => chrome.system.display.getInfo(r));
  const pb = displayInfo[0]?.bounds || { width: 0, height: 0 };
  const res = `${pb.width}x${pb.height}-${displayInfo.length}`;
  const userAgent = navigator.userAgent;
  // Simple hardware fingerprint combine with timezone
  return btoa(`${res}-${userAgent}-${Intl.DateTimeFormat().resolvedOptions().timeZone}`);
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

const CHEATING_TOOL_SIGNATURES = {
  // Port-based detection (Cluely runs Vite dev server on these ports)
  ports: [5180, 5173, 5174],

  // Known cheating tool window title patterns
  titlePatterns: [
    'interview coder', 'cluely', 'free-cluely', 'free cluely',
    'interviewcoder', 'ai overlay', 'screen overlay',
    'cheat sheet', 'exam helper', 'answer overlay',
    'ghostwriter', 'exam.ai',
  ],

  // Known cheating tool URLs
  urlPatterns: [
    'cluely.com', 'interviewcoder.co', 'free-cluely',
    'localhost:5180', '127.0.0.1:5180',
    'localhost:5173', '127.0.0.1:5173',
  ],
};

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

  // 1. Port scan — check if Cluely/Interview Coder's local server is running
  for (const port of CHEATING_TOOL_SIGNATURES.ports) {
    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 1500);

      const res = await fetch(`http://localhost:${port}`, {
        method: 'HEAD',
        mode: 'no-cors',
        signal: controller.signal,
      });

      clearTimeout(timeout);

      // If we get ANY response (even opaque), something is running on that port
      detections.push({
        method: 'port_scan',
        port: port,
        message: `Suspicious local server detected on port ${port} (possible cheating tool)`,
      });
    } catch {
      // Connection refused = nothing running = good
    }
  }

  // 2. Window/Tab title scan — check open tabs for cheating tool names
  try {
    const tabs = await chrome.tabs.query({});
    for (const tab of tabs) {
      const title = (tab.title || '').toLowerCase();
      const url = (tab.url || '').toLowerCase();

      // Check title patterns
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

      // Check URL patterns
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

  // 3. Report detections
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
