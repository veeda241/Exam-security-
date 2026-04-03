/**
 * ExamGuard Pro - Popup Script v2.0
 * Premium UI with enhanced error handling and real-time feedback
 */

// ==================== CONFIGURATION ====================
const BACKEND_URL = 'http://127.0.0.1:8000';

const CONFIG = {
    API_BASE: `${BACKEND_URL}/api`,
    HEALTH_CHECK_INTERVAL: 8000, 
    HEALTH_CHECK_ENDPOINT: '/health-check', // Hit /api/health-check
};

// ==================== DOM ELEMENTS ====================
const setupSection = document.getElementById('setup-section');
const activeSection = document.getElementById('active-section');
const setupForm = document.getElementById('setup-form');
const startBtn = document.getElementById('start-btn');
const stopBtn = document.getElementById('stop-btn');
const statusIndicator = document.getElementById('status-indicator');
const connectionStatus = document.getElementById('connection-status');

// Stats elements
const statTabs = document.getElementById('stat-tabs');
const statNoFace = document.getElementById('stat-noface');
const statMultiFace = document.getElementById('stat-multiface');
const statPhone = document.getElementById('stat-phone');
const statAudio = document.getElementById('stat-audio');
const statTime = document.getElementById('stat-time');
const sessionIdDisplay = document.getElementById('session-id-display');


// Permission indicators
const permScreen = document.getElementById('perm-screen');
const permWebcam = document.getElementById('perm-webcam');
const permBackend = document.getElementById('perm-backend');

// Capture status
const screenStatus = document.getElementById('screen-status');
const webcamStatus = document.getElementById('webcam-status');
const syncStatus = document.getElementById('sync-status');

// State
let statsInterval = null;
let startTime = null;
let isBackendConnected = false;

// ==================== INITIALIZATION ====================

document.addEventListener('DOMContentLoaded', async () => {
    console.log('🚀 Popup initializing...');
    
    try {
        // 1. Initial UI state - hide active until confirmed
        activeSection.classList.add('hidden');
        
        // 2. Check current session status with a timeout to prevent blank screen
        const statusPromise = getSessionStatus();
        const timeoutPromise = new Promise(resolve => setTimeout(() => resolve({ active: false, timeout: true }), 2000));
        
        const status = await Promise.race([statusPromise, timeoutPromise]);
        console.log('📊 Session status:', status);

        if (status && status.active) {
            showActiveSession(status);
        } else {
            console.log(status?.timeout ? '⏱️ Status check timed out' : 'ℹ️ No active session');
            showSetupForm();
        }

        // 3. Check backend connection in background (non-blocking for UI reveal)
        checkBackendConnection().catch(err => console.warn('Backend check error:', err));
        
        // 4. Check local permissions
        checkPermissions();

        // 5. Start maintenance cycles
        setInterval(checkBackendConnection, CONFIG.HEALTH_CHECK_INTERVAL);
        
    } catch (error) {
        console.error('❌ Popup initialization failed:', error);
        showSetupForm(); // Emergency fallback to show SOMETHING
    }
});

async function checkBackendConnection() {
    try {
        const url = `${CONFIG.API_BASE}${CONFIG.HEALTH_CHECK_ENDPOINT}`;
        console.log(`[Health] Checking connection to ${url}...`);
        
        const response = await fetch(url, {
            method: 'GET',
            signal: AbortSignal.timeout(30000), // 30s to handle Render cold start
        });

        if (response.ok) {
            isBackendConnected = true;
            connectionStatus.classList.remove('offline');
            connectionStatus.innerHTML = '<span class="connection-dot"></span><span>Backend Connected</span>';
            permBackend.textContent = '✅';
            permBackend.classList.add('granted');
        } else {
            console.warn(`[Health] Backend status code: ${response.status}`);
            throw new Error(`Backend responded with ${response.status}`);
        }
    } catch (error) {
        console.warn('[Health] Backend check failed:', error.message);
        isBackendConnected = false;
        connectionStatus.classList.add('offline');
        connectionStatus.innerHTML = '<span class="connection-dot"></span><span>Backend Offline</span>';
        permBackend.textContent = '❌';
        permBackend.classList.remove('granted');
    }
}

async function getSessionStatus() {
    return new Promise((resolve) => {
        chrome.runtime.sendMessage({ type: 'GET_STATUS' }, (response) => {
            resolve(response);
        });
    });
}

async function checkPermissions() {
    try {
        const hasMedia = !!navigator.mediaDevices;
        const hasScreen = !!navigator.mediaDevices?.getDisplayMedia;
        const hasWebcam = !!navigator.mediaDevices?.getUserMedia;

        if (hasScreen) {
            permScreen.textContent = '✅';
            permScreen.classList.add('granted');
        }

        if (hasWebcam) {
            permWebcam.textContent = '✅';
            permWebcam.classList.add('granted');
        }
    } catch (error) {
        console.error('Permission check failed:', error);
    }
}

// ==================== UI STATE MANAGEMENT ====================

function showSetupForm() {
    setupSection.classList.remove('hidden');
    activeSection.classList.add('hidden');
    statusIndicator.classList.remove('active');
    statusIndicator.classList.add('inactive');
    statusIndicator.querySelector('.status-text').textContent = 'Offline';
}

function showActiveSession(status) {
    // Populate data BEFORE revealing section to prevent flickering
    if (status.sessionId) {
        sessionIdDisplay.textContent = status.sessionId.substring(0, 8).toUpperCase();
    }
    
    // Set initial timer reference
    startTime = Date.now() - (status.duration || 0);
    updateTimer(); // Initial tick
    
    // Update initial stats
    updateStats(status);
    updateCaptureStatus(status);

    // Reveal the correct section
    setupSection.classList.add('hidden');
    activeSection.classList.remove('hidden');
    
    // Update header status
    statusIndicator.classList.remove('inactive');
    statusIndicator.classList.add('active');
    statusIndicator.querySelector('.status-text').textContent = 'Live';

    // Start background refresh
    startStatsInterval();
}

function updateStats(status) {
    if (statTabs) animateNumber(statTabs, status.tabSwitchCount || 0);
    if (statNoFace) animateNumber(statNoFace, status.nofaceCount || 0);
    if (statMultiFace) animateNumber(statMultiFace, status.multifaceCount || 0);
    if (statPhone) animateNumber(statPhone, status.phoneCount || 0);
    if (statAudio) animateNumber(statAudio, status.audioAnomalyCount || 0);
    
    // Update browsing tracker stats
    updateBrowsingStats(status.browsing, status.globalRiskScore, status.globalEffortScore);
}

/** Update the browsing monitor section in the popup */
function updateBrowsingStats(browsing, globalRisk, globalEffort) {
    if (!browsing) return;
    
    const actualRisk = globalRisk !== undefined ? globalRisk : browsing.browsingRiskScore;
    const actualEffort = globalEffort !== undefined ? globalEffort : browsing.effortScore;
    
    // Risk score
    const riskEl = document.getElementById('browsing-risk');
    const riskBar = document.getElementById('risk-bar');
    if (riskEl) {
        riskEl.textContent = Math.round(actualRisk);
        riskBar.style.width = `${Math.min(100, actualRisk)}%`;
        // Color: green→yellow→red
        if (actualRisk < 30) {
            riskBar.style.background = 'linear-gradient(90deg, #10b981, #34d399)';
        } else if (actualRisk < 60) {
            riskBar.style.background = 'linear-gradient(90deg, #f59e0b, #fbbf24)';
        } else {
            riskBar.style.background = 'linear-gradient(90deg, #ef4444, #f87171)';
        }
    }
    
    // Effort score
    const effortEl = document.getElementById('browsing-effort');
    const effortBar = document.getElementById('effort-bar');
    if (effortEl) {
        effortEl.textContent = Math.round(actualEffort);
        effortBar.style.width = `${Math.min(100, actualEffort)}%`;
        if (actualEffort > 70) {
            effortBar.style.background = 'linear-gradient(90deg, #10b981, #34d399)';
        } else if (actualEffort > 40) {
            effortBar.style.background = 'linear-gradient(90deg, #f59e0b, #fbbf24)';
        } else {
            effortBar.style.background = 'linear-gradient(90deg, #ef4444, #f87171)';
        }
    }
    
    // Open tabs count
    const openTabsEl = document.getElementById('open-tabs-count');
    if (openTabsEl) openTabsEl.textContent = browsing.openTabsCount || 0;
    
    // Flagged tabs
    const flaggedBadge = document.getElementById('flagged-tabs-badge');
    const flaggedCount = document.getElementById('flagged-tabs-count');
    if (flaggedBadge && browsing.flaggedOpenTabs > 0) {
        flaggedBadge.style.display = 'inline';
        flaggedCount.textContent = browsing.flaggedOpenTabs;
    } else if (flaggedBadge) {
        flaggedBadge.style.display = 'none';
    }
    
    // Sites visited
    const sitesEl = document.getElementById('sites-visited');
    if (sitesEl) {
        const flagged = browsing.flaggedSitesCount || 0;
        sitesEl.textContent = `${browsing.totalSitesVisited || 0}${flagged > 0 ? ` (${flagged} flagged)` : ''}`;
    }
    
    // Exam focus percentage
    const focusEl = document.getElementById('exam-focus');
    if (focusEl && browsing.totalTime > 0) {
        const productiveTime = (browsing.timeByCategory?.exam || 0) + (browsing.timeByCategory?.learning || 0);
        const pct = Math.round((productiveTime / browsing.totalTime) * 100);
        focusEl.textContent = `${pct}%`;
        focusEl.style.color = pct > 70 ? '#10b981' : pct > 40 ? '#f59e0b' : '#ef4444';
    }
    
    // Active site
    const activeContainer = document.getElementById('active-site-container');
    const activeName = document.getElementById('active-site-name');
    const activeBadge = document.getElementById('active-site-badge');
    if (activeContainer && browsing.activeSite) {
        activeContainer.style.display = 'flex';
        // Show short hostname
        try {
            activeName.textContent = new URL(browsing.activeSite.url).hostname.replace('www.', '').substring(0, 25);
        } catch {
            activeName.textContent = browsing.activeSite.url?.substring(0, 25) || 'Unknown';
        }
        
        const cat = browsing.activeSite.category;
        activeBadge.textContent = cat.toUpperCase();
        activeBadge.className = `category-badge cat-${cat}`;
    } else if (activeContainer) {
        activeContainer.style.display = 'none';
    }
}

function animateNumber(element, targetValue) {
    const currentValue = parseInt(element.textContent) || 0;
    if (currentValue !== targetValue) {
        element.textContent = targetValue;
        element.style.transform = 'scale(1.2)';
        setTimeout(() => {
            element.style.transform = 'scale(1)';
        }, 200);
    }
}

function updateTimer() {
    if (!startTime) return;

    const elapsed = Math.floor((Date.now() - startTime) / 1000);
    const hours = Math.floor(elapsed / 3600);
    const minutes = Math.floor((elapsed % 3600) / 60);
    const seconds = elapsed % 60;

    if (hours > 0) {
        statTime.textContent = `${hours}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    } else {
        statTime.textContent = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }
}

function startStatsInterval() {
    if (statsInterval) clearInterval(statsInterval);

    statsInterval = setInterval(async () => {
        updateTimer();
        const status = await getSessionStatus();
        if (status && status.active) {
            updateStats(status);
            updateCaptureStatus(status);
        }
    }, 1000);
}

function updateCaptureStatus(status) {
    // Update capture indicators based on recent activity
    if (status.lastScreenCapture && Date.now() - status.lastScreenCapture < 5000) {
        screenStatus.classList.add('active');
    }
    if (status.lastWebcamCapture && Date.now() - status.lastWebcamCapture < 7000) {
        webcamStatus.classList.add('active');
    }
    if (status.lastSync && Date.now() - status.lastSync < 15000) {
        syncStatus.classList.add('active');
    }
}

function stopStatsInterval() {
    if (statsInterval) {
        clearInterval(statsInterval);
        statsInterval = null;
    }
}

// ==================== EVENT HANDLERS ====================

setupForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    if (!isBackendConnected) {
        showNotification('Cannot start exam: Backend is offline', 'error');
        return;
    }

    const studentName = document.getElementById('student-name').value.trim();
    const studentId = document.getElementById('student-id').value.trim();
    const examId = document.getElementById('exam-id').value.trim();

    if (!studentName || !studentId || !examId) {
        showNotification('Please fill in all fields', 'warning');
        return;
    }

    startBtn.disabled = true;
    startBtn.innerHTML = '<span class="btn-icon">⏳</span> Initializing...';

    try {
        const response = await new Promise((resolve) => {
            chrome.runtime.sendMessage({
                type: 'START_EXAM',
                data: { studentName, studentId, examId }
            }, resolve);
        });

        if (response && response.success) {
            showNotification('Please grant permissions in the new window', 'info');
            setTimeout(() => window.close(), 300);
        } else {
            const errMsg = response?.error || 'Failed to start exam';
            if (errMsg.includes('Invalid exam code') || errMsg.includes('not been initiated')) {
                showNotification('❌ Invalid exam code! Ask your proctor for the correct code.', 'error');
            } else {
                showNotification('Failed: ' + errMsg, 'error');
            }
        }
    } catch (error) {
        console.error('Start exam failed:', error);
        showNotification('Failed: ' + error.message, 'error');
    }

    startBtn.disabled = false;
    startBtn.innerHTML = '<span class="btn-icon">▶️</span> Start Proctoring';
});

stopBtn.addEventListener('click', async () => {
    if (!confirm('Are you sure you want to end the exam session?\n\nAll recorded data will be submitted.')) {
        return;
    }

    stopBtn.disabled = true;
    stopBtn.innerHTML = '<span class="btn-icon">⏳</span> Submitting...';

    try {
        const response = await new Promise((resolve) => {
            chrome.runtime.sendMessage({ type: 'STOP_EXAM' }, resolve);
        });

        stopStatsInterval();
        showSetupForm();

        if (response.success && response.summary) {
            const s = response.summary;
            showNotification(
                `Session ended!\n\n` +
                `Duration: ${formatDuration(s.duration)}\n` +
                `Events: ${s.totalEvents}`,
                'success'
            );
        }
    } catch (error) {
        console.error('Stop exam failed:', error);
        showNotification('Failed to stop: ' + error.message, 'error');
    }

    stopBtn.disabled = false;
    stopBtn.innerHTML = '<span class="btn-icon">⏹️</span> End Exam Session';
});

// ==================== UTILITIES ====================

function formatDuration(ms) {
    const seconds = Math.floor(ms / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);

    if (hours > 0) {
        return `${hours}h ${minutes % 60}m`;
    } else if (minutes > 0) {
        return `${minutes}m ${seconds % 60}s`;
    } else {
        return `${seconds}s`;
    }
}

function showNotification(message, type = 'info') {
    // Create toast notification
    const existing = document.querySelector('.toast-notification');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = `toast-notification toast-${type}`;
    toast.style.cssText = `
        position: fixed;
        bottom: 80px;
        left: 50%;
        transform: translateX(-50%);
        padding: 12px 20px;
        border-radius: 10px;
        font-size: 13px;
        font-weight: 600;
        z-index: 1000;
        animation: slideUp 0.3s ease;
        max-width: 320px;
        text-align: center;
        backdrop-filter: blur(10px);
    `;

    const colors = {
        error: 'background: rgba(239, 68, 68, 0.9); color: white;',
        success: 'background: rgba(16, 185, 129, 0.9); color: white;',
        warning: 'background: rgba(245, 158, 11, 0.9); color: white;',
        info: 'background: rgba(124, 58, 237, 0.9); color: white;',
    };

    toast.style.cssText += colors[type] || colors.info;
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'fadeOut 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// Add fadeOut animation
const style = document.createElement('style');
style.textContent = `
    @keyframes fadeOut {
        from { opacity: 1; transform: translateX(-50%) translateY(0); }
        to { opacity: 0; transform: translateX(-50%) translateY(10px); }
    }
`;
document.head.appendChild(style);
