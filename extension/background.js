/**
 * ExamGuard Pro - Background Service Worker v2.0
 * Enhanced session management, robust error handling, and retry logic
 */

// ==================== CONFIGURATION ====================
// Change BACKEND_URL to your deployed server URL
// For local dev: 'http://localhost:8000'
// For cloud:     'https://exam-security.onrender.com'
const BACKEND_URL = 'https://exam-security.onrender.com';

const CONFIG = {
  API_BASE: `${BACKEND_URL}/api`,
  WS_URL: `${BACKEND_URL.replace('https://', 'wss://').replace('http://', 'ws://')}/ws/student`,
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
    
    // Update visited sites list
    this.recordVisit(url, title, category, riskLevel);
    
    // Recalculate scores
    this.calculateScores();
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
    
    risk += aiTimeRatio * 80;             // AI usage: up to 80 risk
    risk += cheatingTimeRatio * 100;      // Cheating: up to 100 risk
    risk += entertainmentTimeRatio * 50;  // Entertainment: up to 50 risk
    
    // Count-based risk (unique flagged sites)
    const flaggedSites = this.visitedSites.filter(s => ['ai', 'cheating', 'entertainment'].includes(s.category));
    risk += Math.min(flaggedSites.length * 5, 25); // Up to 25 from site count
    
    // Open tabs risk bonus
    const flaggedOpenTabs = this.openTabs.filter(t => t.riskLevel !== 'none').length;
    risk += Math.min(flaggedOpenTabs * 3, 15); // Up to 15 from open tabs
    
    this.browsingRiskScore = Math.min(Math.round(risk), 100);
    
    // --- Effort Score (0-100) ---
    // Effort is purely based on how much time was spent on exam vs non-exam.
    // If student spends 100% on exam + learning => effort 100. If 0% => effort 0.
    const productiveTime = this.timeByCategory.exam + (this.timeByCategory.learning || 0);
    const productiveRatio = productiveTime / totalTime;
    const distractionTime = this.timeByCategory.ai + this.timeByCategory.cheating + this.timeByCategory.entertainment;
    const distractionRatio = distractionTime / totalTime;
    const otherRatio = this.timeByCategory.other / totalTime;
    
    // Base effort: productive time (exam + learning) drives it up, everything else drives it down
    let effort = productiveRatio * 100;
    
    // "Other" (unknown/unclassified sites) gets very little credit
    effort += otherRatio * 10;
    
    // Extra penalty for known distraction sites beyond ratio
    effort -= Math.min(flaggedSites.length * 4, 25);
    
    // Bonus: if >80% exam/learning time, small bonus. Student is focused.
    if (productiveRatio > 0.8) effort += 10;
    
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
        examTimePercent: totalTime > 0 ? Math.round((this.timeByCategory.exam / totalTime) * 100) : 0,
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
      iconUrl: 'icons/icon48.png',
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
        const response = await fetch(`${CONFIG.API_BASE}/sessions/create`, {
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

    // Start browsing tracker
    browsingTracker.start();

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

    // Stop browsing tracker and send final summary
    const browsingSummary = browsingTracker.generateSummaryEvent();
    logEvent(browsingSummary);
    await syncEvents(); // Sync the browsing summary
    browsingTracker.stop();

    // End session on backend
    try {
      await fetch(`${CONFIG.API_BASE}/sessions/${examSession.sessionId}/end`, {
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
        // Browsing tracker data
        browsing: examSession.active ? browsingTracker.getStats() : null,
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
          iconUrl: 'icons/icon48.png',
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
