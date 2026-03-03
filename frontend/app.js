/**
 * ExamGuard Pro - Enhanced Dashboard Application
 * Modern, real-time exam proctoring dashboard
 */

// =============================================================================
// Configuration
// =============================================================================
// Detect environment
const isProduction = window.location.protocol === 'https:';
const isFileProtocol = window.location.protocol === 'file:';
const isDevServer = window.location.port !== '8000' && !isFileProtocol;

// API Base URL
// If running on port 8000 (backend), use relative path
// If running on dev server (e.g. 5500) or file://, point to localhost:8000
const API_BASE = (isFileProtocol || isDevServer)
    ? 'http://localhost:8000/api'
    : '/api';

// WebSocket URL
const WS_PROTOCOL = isProduction ? 'wss:' : 'ws:';
const WS_HOST = (isFileProtocol || isDevServer) ? 'localhost:8000' : window.location.host;

const CONFIG = {
    API_BASE: API_BASE,
    WS_URL: `${WS_PROTOCOL}//${WS_HOST}/ws/dashboard`,
    REFRESH_INTERVAL: 30000,
    MAX_RECONNECT_ATTEMPTS: 5,
    ACTIVITY_MAX_ITEMS: 50,
    TOAST_DURATION: 5000,
};

// =============================================================================
// State Management
// =============================================================================
const State = {
    students: [],
    sessions: [],
    alerts: [],
    activities: [],
    filters: {
        search: '',
        status: 'all',
        session: 'all',
    },
    sort: {
        field: 'risk_score',
        direction: 'desc',
    },
    websocket: null,
    reconnectAttempts: 0,
    isConnected: false,
};

// =============================================================================
// DOM Elements
// =============================================================================
const Elements = {
    // Stats
    totalStudents: document.getElementById('totalStudents'),
    highRiskCount: document.getElementById('highRiskCount'),
    avgEngagement: document.getElementById('avgEngagement'),
    avgEffort: document.getElementById('avgEffort'),

    // Table
    studentTableBody: document.getElementById('studentTableBody'),
    shownCount: document.getElementById('shownCount'),
    totalCount: document.getElementById('totalCount'),

    // Filters
    statusFilter: document.getElementById('statusFilter'),
    sessionFilter: document.getElementById('sessionFilter'),
    globalSearch: document.getElementById('globalSearch'),

    // Connection
    connectionStatus: document.getElementById('connectionStatus'),
    currentTime: document.getElementById('currentTime'),

    // Activity
    activityFeed: document.getElementById('activityFeed'),

    // Chart
    safeCount: document.getElementById('safeCount'),
    reviewCount: document.getElementById('reviewCount'),
    suspiciousCount: document.getElementById('suspiciousCount'),
    safePercentage: document.getElementById('safePercentage'),

    // Navigation
    sidebar: document.getElementById('sidebar'),
    sidebarToggle: document.getElementById('sidebarToggle'),
    mobileMenuBtn: document.getElementById('mobileMenuBtn'),
    navItems: document.querySelectorAll('.nav-item'),

    // Badges
    alertCount: document.getElementById('alertCount'),
    activeSessionCount: document.getElementById('activeSessionCount'),
    notificationBadge: document.getElementById('notificationBadge'),

    // Modal
    studentModal: document.getElementById('studentModal'),
    modalStudentName: document.getElementById('modalStudentName'),
    modalBody: document.getElementById('modalBody'),

    // Toast
    toastContainer: document.getElementById('toastContainer'),

    // Theme
    themeToggle: document.getElementById('themeToggle'),
};

// =============================================================================
// Initialization
// =============================================================================
document.addEventListener('DOMContentLoaded', () => {
    initializeApp();
});

function initializeApp() {
    console.log('[ExamGuard] Initializing dashboard...');

    // Setup event listeners
    setupEventListeners();

    // Start clock
    updateTime();
    setInterval(updateTime, 1000);

    // Load initial data
    fetchStudentData();
    fetchSessions();

    // Connect WebSocket
    connectWebSocket();

    // Setup auto-refresh fallback
    setInterval(() => {
        if (!State.isConnected) {
            fetchStudentData();
        }
    }, CONFIG.REFRESH_INTERVAL);

    // Load theme preference
    loadTheme();

    console.log('[ExamGuard] Dashboard initialized!');
}

// =============================================================================
// Event Listeners
// =============================================================================
function setupEventListeners() {
    // Sidebar toggle
    Elements.sidebarToggle?.addEventListener('click', () => {
        Elements.sidebar.classList.toggle('collapsed');
    });

    // Mobile menu
    Elements.mobileMenuBtn?.addEventListener('click', () => {
        Elements.sidebar.classList.toggle('open');
    });

    // Navigation
    Elements.navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const view = item.dataset.view;
            switchView(view);
        });
    });

    // Filters
    Elements.statusFilter?.addEventListener('change', applyFilters);
    Elements.sessionFilter?.addEventListener('change', applyFilters);
    Elements.globalSearch?.addEventListener('input', debounce(applyFilters, 300));

    // Theme toggle
    Elements.themeToggle?.addEventListener('click', toggleTheme);

    // Modal close on backdrop click
    Elements.studentModal?.addEventListener('click', (e) => {
        if (e.target.classList.contains('modal-backdrop')) {
            closeModal();
        }
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', handleKeyboardShortcuts);

    // Table sorting
    document.querySelectorAll('.data-table th.sortable').forEach(th => {
        th.addEventListener('click', () => {
            const field = th.dataset.sort;
            handleSort(field);
        });
    });

    // Clear activity
    document.getElementById('clearActivity')?.addEventListener('click', clearActivity);
}

function handleKeyboardShortcuts(e) {
    // Cmd/Ctrl + K for search
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        Elements.globalSearch?.focus();
    }

    // Escape to close modal
    if (e.key === 'Escape') {
        closeModal();
    }
}

// =============================================================================
// WebSocket Connection
// =============================================================================
function connectWebSocket() {
    try {
        State.websocket = new WebSocket(CONFIG.WS_URL);

        State.websocket.onopen = () => {
            console.log('[WS] Connected');
            State.isConnected = true;
            State.reconnectAttempts = 0;
            updateConnectionStatus(true);

            // Start heartbeat
            setInterval(() => {
                if (State.websocket?.readyState === WebSocket.OPEN) {
                    State.websocket.send('ping');
                }
            }, 25000);
        };

        State.websocket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                handleWebSocketMessage(data);
            } catch (e) {
                console.error('[WS] Parse error:', e);
            }
        };

        State.websocket.onclose = () => {
            console.log('[WS] Disconnected');
            State.isConnected = false;
            updateConnectionStatus(false);
            attemptReconnect();
        };

        State.websocket.onerror = (error) => {
            console.error('[WS] Error:', error);
        };

    } catch (e) {
        console.error('[WS] Connection failed:', e);
        updateConnectionStatus(false);
    }
}

function attemptReconnect() {
    if (State.reconnectAttempts < CONFIG.MAX_RECONNECT_ATTEMPTS) {
        State.reconnectAttempts++;
        const delay = Math.min(1000 * Math.pow(2, State.reconnectAttempts), 30000);
        console.log(`[WS] Reconnecting in ${delay / 1000}s...`);
        setTimeout(connectWebSocket, delay);
    }
}

function updateConnectionStatus(connected) {
    const status = Elements.connectionStatus;
    if (!status) return;

    status.className = `connection-status ${connected ? 'connected' : 'disconnected'}`;
    status.querySelector('.status-text').textContent = connected ? 'Live' : 'Offline';
}

function handleWebSocketMessage(data) {
    const eventType = data.event_type || data.type;

    switch (eventType) {
        case 'heartbeat':
            break;

        case 'pong':
            break;

        case 'risk_score_update':
            handleRiskUpdate(data);
            break;

        case 'student_joined':
        case 'student_left':
            handleStudentPresence(data);
            break;

        case 'alert_triggered':
        case 'face_missing':
        case 'multiple_faces':
        case 'plagiarism_detected':
        case 'unusual_behavior':
        case 'tab_switch':
        case 'copy_paste':
            handleAlert(data);
            break;

        default:
            console.log('[WS] Event:', eventType, data);
    }
}

function handleRiskUpdate(data) {
    const { student_id, data: eventData } = data;

    const studentIndex = State.students.findIndex(
        s => s.id === student_id || s.student_id === student_id
    );

    if (studentIndex >= 0) {
        State.students[studentIndex].risk_score = eventData.risk_score;
        State.students[studentIndex].status = getRiskStatus(eventData.risk_score);
        renderStudentTable();
        updateStats();
        updateChart();
    }

    // Add to activity feed
    addActivity({
        type: eventData.risk_score > 60 ? 'danger' : eventData.risk_score > 30 ? 'warning' : 'info',
        icon: 'fa-chart-line',
        title: 'Risk Score Updated',
        description: `Student ${student_id}: ${Math.round(eventData.risk_score)}%`,
    });

    // Show toast for high risk
    if (eventData.risk_score > 60) {
        showToast({
            type: 'error',
            title: 'High Risk Detected',
            message: `Student ${student_id} has a risk score of ${Math.round(eventData.risk_score)}%`,
        });
    }
}

function handleStudentPresence(data) {
    const isJoining = data.event_type === 'student_joined';

    addActivity({
        type: isJoining ? 'success' : 'info',
        icon: isJoining ? 'fa-user-plus' : 'fa-user-minus',
        title: isJoining ? 'Student Joined' : 'Student Left',
        description: data.student_id || 'Unknown student',
    });

    fetchStudentData();
}

function handleAlert(data) {
    const eventType = data.event_type || data.type;
    const alertData = data.data || {};

    // Add to activity
    addActivity({
        type: 'danger',
        icon: getAlertIcon(eventType),
        title: formatEventType(eventType),
        description: alertData.message || `Student: ${data.student_id}`,
    });

    // Show toast
    showToast({
        type: 'warning',
        title: formatEventType(eventType),
        message: alertData.message || `Alert for student ${data.student_id}`,
    });

    // Update badge
    const currentCount = parseInt(Elements.alertCount?.textContent || '0');
    if (Elements.alertCount) {
        Elements.alertCount.textContent = currentCount + 1;
    }
    if (Elements.notificationBadge) {
        Elements.notificationBadge.textContent = currentCount + 1;
    }
}

// =============================================================================
// Data Fetching
// =============================================================================
async function fetchStudentData() {
    try {
        const response = await fetch(`${CONFIG.API_BASE}/analysis/dashboard`);
        if (!response.ok) throw new Error('Failed to fetch student data');

        State.students = await response.json();
        renderStudentTable();
        updateStats();
        updateChart();

    } catch (error) {
        console.error('[API] Error fetching students:', error);
        showToast({
            type: 'error',
            title: 'Connection Error',
            message: 'Failed to load student data',
        });
    }
}

async function fetchSessions() {
    try {
        const response = await fetch(`${CONFIG.API_BASE}/sessions`);
        if (!response.ok) throw new Error('Failed to fetch sessions');

        State.sessions = await response.json();
        updateSessionFilter();

        if (Elements.activeSessionCount) {
            Elements.activeSessionCount.textContent = State.sessions.length;
        }

    } catch (error) {
        console.error('[API] Error fetching sessions:', error);
    }
}

// =============================================================================
// Rendering
// =============================================================================
function renderStudentTable() {
    const tbody = Elements.studentTableBody;
    if (!tbody) return;

    // Apply filters
    let filtered = filterStudents(State.students);

    // Apply sort
    filtered = sortStudents(filtered);

    // Update counts
    if (Elements.shownCount) Elements.shownCount.textContent = filtered.length;
    if (Elements.totalCount) Elements.totalCount.textContent = State.students.length;

    if (filtered.length === 0) {
        tbody.innerHTML = `
            <tr class="loading-row">
                <td colspan="6">
                    <div class="loading-spinner">
                        <i class="fas fa-inbox"></i>
                        <span>No students found</span>
                    </div>
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = filtered.map(student => renderStudentRow(student)).join('');
}

function renderStudentRow(student) {
    const status = student.status || getRiskStatus(student.risk_score);
    const riskClass = getRiskClass(student.risk_score);
    const initials = getInitials(student.name);

    return `
        <tr data-student-id="${student.student_id || student.id}">
            <td>
                <div class="student-cell">
                    <div class="student-avatar">${initials}</div>
                    <div class="student-info">
                        <span class="student-name">${escapeHtml(student.name)}</span>
                        <span class="student-email">${escapeHtml(student.email)}</span>
                    </div>
                </div>
            </td>
            <td>
                <span class="badge badge-${status}">${status.toUpperCase()}</span>
            </td>
            <td>
                <div class="risk-score">
                    <span class="risk-value ${riskClass}">${Math.round(student.risk_score)}</span>
                </div>
            </td>
            <td>
                <div class="progress-bar">
                    <div class="progress-fill blue" style="width: ${student.engagement_score || 0}%"></div>
                </div>
                <span class="text-muted" style="font-size: 0.75rem;">${Math.round(student.engagement_score || 0)}%</span>
            </td>
            <td>
                <div class="progress-bar">
                    <div class="progress-fill purple" style="width: ${student.effort_alignment || 0}%"></div>
                </div>
                <span class="text-muted" style="font-size: 0.75rem;">${Math.round(student.effort_alignment || 0)}%</span>
            </td>
            <td>
                <button class="btn-details" style="margin-right: 4px;" onclick="viewStudentDetails('${student.student_id || student.id}')">
                    <i class="fas fa-eye"></i> View
                </button>
                <button class="btn-details" style="background-color: var(--bg-secondary); color: var(--accent-yellow); border-color: var(--accent-yellow);" onclick="warnStudent('${student.student_id || student.id}')">
                    <i class="fas fa-exclamation-triangle"></i> Warn
                </button>
            </td>
        </tr>
    `;
}

function updateStats() {
    const students = State.students;

    if (Elements.totalStudents) {
        Elements.totalStudents.textContent = students.length;
    }

    if (Elements.highRiskCount) {
        const highRisk = students.filter(s => (s.risk_score || 0) > 60).length;
        Elements.highRiskCount.textContent = highRisk;
    }

    if (Elements.avgEngagement) {
        const total = students.reduce((acc, s) => acc + (s.engagement_score || 0), 0);
        const avg = students.length ? Math.round(total / students.length) : 0;
        Elements.avgEngagement.textContent = `${avg}%`;
    }

    if (Elements.avgEffort) {
        const total = students.reduce((acc, s) => acc + (s.effort_alignment || 0), 0);
        const avg = students.length ? Math.round(total / students.length) : 0;
        Elements.avgEffort.textContent = `${avg}%`;
    }
}

function updateChart() {
    const students = State.students;
    const total = students.length || 1;

    const safe = students.filter(s => getRiskStatus(s.risk_score) === 'safe').length;
    const review = students.filter(s => getRiskStatus(s.risk_score) === 'review').length;
    const suspicious = students.filter(s => getRiskStatus(s.risk_score) === 'suspicious').length;

    // Update counts
    if (Elements.safeCount) Elements.safeCount.textContent = safe;
    if (Elements.reviewCount) Elements.reviewCount.textContent = review;
    if (Elements.suspiciousCount) Elements.suspiciousCount.textContent = suspicious;

    // Update percentage
    if (Elements.safePercentage) {
        Elements.safePercentage.textContent = `${Math.round((safe / total) * 100)}%`;
    }

    // Update donut chart segments
    const circumference = 2 * Math.PI * 40; // radius = 40

    const safePercent = safe / total;
    const reviewPercent = review / total;
    const suspiciousPercent = suspicious / total;

    const safeSegment = document.querySelector('.donut-segment.safe');
    const reviewSegment = document.querySelector('.donut-segment.review');
    const suspiciousSegment = document.querySelector('.donut-segment.suspicious');

    if (safeSegment) {
        safeSegment.style.strokeDasharray = `${safePercent * circumference} ${circumference}`;
        safeSegment.style.strokeDashoffset = '0';
    }

    if (reviewSegment) {
        reviewSegment.style.strokeDasharray = `${reviewPercent * circumference} ${circumference}`;
        reviewSegment.style.strokeDashoffset = `-${safePercent * circumference}`;
    }

    if (suspiciousSegment) {
        suspiciousSegment.style.strokeDasharray = `${suspiciousPercent * circumference} ${circumference}`;
        suspiciousSegment.style.strokeDashoffset = `-${(safePercent + reviewPercent) * circumference}`;
    }
}

function updateSessionFilter() {
    const select = Elements.sessionFilter;
    if (!select) return;

    select.innerHTML = '<option value="all">All Sessions</option>';

    State.sessions.forEach(session => {
        const option = document.createElement('option');
        option.value = session.id;
        option.textContent = session.name || `Session ${session.id}`;
        select.appendChild(option);
    });
}

// =============================================================================
// Activity Feed
// =============================================================================
function addActivity(activity) {
    State.activities.unshift({
        ...activity,
        timestamp: new Date(),
    });

    // Limit items
    if (State.activities.length > CONFIG.ACTIVITY_MAX_ITEMS) {
        State.activities = State.activities.slice(0, CONFIG.ACTIVITY_MAX_ITEMS);
    }

    renderActivityFeed();
}

function renderActivityFeed() {
    const feed = Elements.activityFeed;
    if (!feed) return;

    if (State.activities.length === 0) {
        feed.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-inbox"></i>
                <p>No recent activity</p>
            </div>
        `;
        return;
    }

    feed.innerHTML = State.activities.slice(0, 10).map(activity => `
        <div class="activity-item">
            <div class="activity-icon ${activity.type}">
                <i class="fas ${activity.icon}"></i>
            </div>
            <div class="activity-content">
                <div class="activity-title">${escapeHtml(activity.title)}</div>
                <div class="activity-desc">${escapeHtml(activity.description)}</div>
            </div>
            <span class="activity-time">${formatTime(activity.timestamp)}</span>
        </div>
    `).join('');
}

function clearActivity() {
    State.activities = [];
    renderActivityFeed();
}

// =============================================================================
// Filtering & Sorting
// =============================================================================
function filterStudents(students) {
    return students.filter(student => {
        // Search filter
        if (State.filters.search) {
            const search = State.filters.search.toLowerCase();
            const matchesName = student.name?.toLowerCase().includes(search);
            const matchesEmail = student.email?.toLowerCase().includes(search);
            if (!matchesName && !matchesEmail) return false;
        }

        // Status filter
        if (State.filters.status !== 'all') {
            const status = getRiskStatus(student.risk_score);
            if (status !== State.filters.status) return false;
        }

        // Session filter
        if (State.filters.session !== 'all') {
            if (student.session_id !== State.filters.session) return false;
        }

        return true;
    });
}

function sortStudents(students) {
    return [...students].sort((a, b) => {
        let aVal = a[State.sort.field];
        let bVal = b[State.sort.field];

        if (typeof aVal === 'string') {
            aVal = aVal.toLowerCase();
            bVal = bVal.toLowerCase();
        }

        if (State.sort.direction === 'asc') {
            return aVal > bVal ? 1 : -1;
        } else {
            return aVal < bVal ? 1 : -1;
        }
    });
}

function applyFilters() {
    State.filters.search = Elements.globalSearch?.value || '';
    State.filters.status = Elements.statusFilter?.value || 'all';
    State.filters.session = Elements.sessionFilter?.value || 'all';

    renderStudentTable();
}

function handleSort(field) {
    if (State.sort.field === field) {
        State.sort.direction = State.sort.direction === 'asc' ? 'desc' : 'asc';
    } else {
        State.sort.field = field;
        State.sort.direction = 'desc';
    }

    renderStudentTable();
}

// =============================================================================
// Modal
// =============================================================================
function viewStudentDetails(studentId) {
    const student = State.students.find(
        s => s.student_id === studentId || s.id === studentId
    );

    if (!student) return;

    if (Elements.modalStudentName) {
        Elements.modalStudentName.textContent = student.name;
    }

    if (Elements.modalBody) {
        Elements.modalBody.innerHTML = `
            <div class="student-detail-grid">
                <div class="detail-section">
                    <h4><i class="fas fa-user"></i> Student Information</h4>
                    <div class="detail-row">
                        <span class="detail-label">Name</span>
                        <span class="detail-value">${escapeHtml(student.name)}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Email</span>
                        <span class="detail-value">${escapeHtml(student.email)}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Student ID</span>
                        <span class="detail-value">${student.student_id || student.id}</span>
                    </div>
                </div>
                
                <div class="detail-section">
                    <h4><i class="fas fa-chart-line"></i> Risk Analysis</h4>
                    <div class="detail-row">
                        <span class="detail-label">Risk Score</span>
                        <span class="detail-value ${getRiskClass(student.risk_score)}">
                            ${Math.round(student.risk_score)}%
                        </span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Status</span>
                        <span class="badge badge-${getRiskStatus(student.risk_score)}">
                            ${getRiskStatus(student.risk_score).toUpperCase()}
                        </span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Engagement</span>
                        <span class="detail-value">${Math.round(student.engagement_score || 0)}%</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Effort Alignment</span>
                        <span class="detail-value">${Math.round(student.effort_alignment || 0)}%</span>
                    </div>
                </div>
            </div>
            
            <style>
                .student-detail-grid { display: grid; gap: 1.5rem; }
                .detail-section { padding: 1rem; background: var(--bg-secondary); border-radius: var(--radius-md); }
                .detail-section h4 { margin-bottom: 1rem; font-size: 0.875rem; color: var(--text-secondary); display: flex; align-items: center; gap: 0.5rem; }
                .detail-section h4 i { color: var(--accent-blue); }
                .detail-row { display: flex; justify-content: space-between; padding: 0.5rem 0; border-bottom: 1px solid var(--border-color); }
                .detail-row:last-child { border-bottom: none; }
                .detail-label { color: var(--text-muted); }
                .detail-value { font-weight: 500; }
            </style>
        `;
    }

    Elements.studentModal?.classList.add('active');
}

function closeModal() {
    Elements.studentModal?.classList.remove('active');
}

function warnStudent(studentId) {
    if (confirm(`Send a warning to student ${studentId}?`)) {
        showToast({
            type: 'warning',
            title: 'Warning Sent',
            message: `Warning issued to student ${studentId}`,
        });
    }
}

window.viewStudentDetails = viewStudentDetails;
window.closeModal = closeModal;
window.warnStudent = warnStudent;

// =============================================================================
// Toast Notifications
// =============================================================================
function showToast({ type = 'info', title, message }) {
    const container = Elements.toastContainer;
    if (!container) return;

    const icons = {
        info: 'fa-info-circle',
        success: 'fa-check-circle',
        warning: 'fa-exclamation-triangle',
        error: 'fa-times-circle',
    };

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <div class="toast-icon">
            <i class="fas ${icons[type]}"></i>
        </div>
        <div class="toast-content">
            <div class="toast-title">${escapeHtml(title)}</div>
            <div class="toast-message">${escapeHtml(message)}</div>
        </div>
        <button class="toast-close" onclick="this.parentElement.remove()">
            <i class="fas fa-times"></i>
        </button>
    `;

    container.appendChild(toast);

    // Auto remove
    setTimeout(() => {
        if (toast.parentElement) {
            toast.style.animation = 'slideInRight 0.3s ease-out reverse';
            setTimeout(() => toast.remove(), 300);
        }
    }, CONFIG.TOAST_DURATION);
}

// =============================================================================
// Quick Actions
// =============================================================================
function sendBroadcast() {
    const message = prompt('Enter broadcast message:');
    if (message) {
        showToast({
            type: 'success',
            title: 'Broadcast Sent',
            message: 'Message sent to all students',
        });
    }
}

function pauseAllSessions() {
    if (confirm('Pause all active sessions?')) {
        showToast({
            type: 'warning',
            title: 'Sessions Paused',
            message: 'All active sessions have been paused',
        });
    }
}

function requestWebcamSnapshotAll() {
    if (confirm('Request snapshot from all active webcams?')) {
        showToast({
            type: 'info',
            title: 'Snapshot Requested',
            message: 'Snapshot requests sent to all active students',
        });
    }
}

function enableStrictMonitoring() {
    if (confirm('Enable strict monitoring for all sessions? This increases ML sensitivity.')) {
        showToast({
            type: 'warning',
            title: 'Strict Monitoring Enabled',
            message: 'Thresholds tightened for behavioral and visual anomalies',
        });
    }
}

function emergencyLockdown() {
    if (confirm('⚠️ EMERGENCY LOCKDOWN: This will lock all sessions immediately. Continue?')) {
        showToast({
            type: 'error',
            title: 'Emergency Lockdown',
            message: 'All sessions have been locked',
        });
    }
}

function endAllSessions() {
    if (confirm('❌ END ALL SESSIONS: Are you sure you want to forcibly stop all exams?')) {
        showToast({
            type: 'error',
            title: 'Sessions Ended',
            message: 'All exams have been disconnected and ended',
        });
    }
}

window.sendBroadcast = sendBroadcast;
window.pauseAllSessions = pauseAllSessions;
window.requestWebcamSnapshotAll = requestWebcamSnapshotAll;
window.enableStrictMonitoring = enableStrictMonitoring;
window.emergencyLockdown = emergencyLockdown;
window.endAllSessions = endAllSessions;

// =============================================================================
// Theme
// =============================================================================
function loadTheme() {
    const theme = localStorage.getItem('examguard-theme') || 'dark';
    document.documentElement.setAttribute('data-theme', theme);
    updateThemeIcon(theme);
}

function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme') || 'dark';
    const next = current === 'dark' ? 'light' : 'dark';

    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('examguard-theme', next);
    updateThemeIcon(next);
}

function updateThemeIcon(theme) {
    const icon = Elements.themeToggle?.querySelector('i');
    if (icon) {
        icon.className = `fas fa-${theme === 'dark' ? 'moon' : 'sun'}`;
    }
}

function switchView(view) {
    // Update nav item active state
    Elements.navItems.forEach(item => {
        item.classList.toggle('active', item.dataset.view === view);
    });

    // Toggle view sections
    document.querySelectorAll('.view-section').forEach(section => {
        section.classList.remove('active');
    });
    const targetView = document.getElementById(`view-${view}`);
    if (targetView) {
        targetView.classList.add('active');
    }

    // Update breadcrumb
    const viewLabels = {
        dashboard: 'Live Monitoring',
        sessions: 'Active Sessions',
        students: 'Student Directory',
        alerts: 'Alert Log',
        reports: 'Reports',
        analytics: 'Analytics',
    };
    const current = document.querySelector('.breadcrumb .current');
    if (current) {
        current.textContent = viewLabels[view] || view.charAt(0).toUpperCase() + view.slice(1);
    }

    // Populate sub-page data when switching
    if (view === 'sessions') populateSessionsView();
    if (view === 'students') populateStudentsView();
    if (view === 'alerts') populateAlertsView();

    // Close mobile sidebar
    Elements.sidebar?.classList.remove('open');
}

// =============================================================================
// Sub-View Renderers
// =============================================================================
function populateSessionsView() {
    const tbody = document.getElementById('sessionsTableBody');
    if (!tbody) return;

    const sessions = State.sessions;
    const countEl = document.getElementById('sessionsActiveCount');
    const participantsEl = document.getElementById('sessionsTotalParticipants');
    const resultsEl = document.getElementById('sessionsResultsCount');

    if (countEl) countEl.textContent = sessions.length;
    if (participantsEl) participantsEl.textContent = State.students.length;

    if (sessions.length === 0) {
        tbody.innerHTML = `<tr class="loading-row"><td colspan="8"><div class="loading-spinner"><i class="fas fa-inbox"></i><span>No active sessions</span></div></td></tr>`;
        if (resultsEl) resultsEl.textContent = 'Showing 0 sessions';
        return;
    }

    tbody.innerHTML = sessions.map(session => {
        const sessionStudents = State.students.filter(s => s.session_id === session.id);
        const avgRisk = sessionStudents.length
            ? Math.round(sessionStudents.reduce((a, s) => a + (s.risk_score || 0), 0) / sessionStudents.length)
            : 0;
        const started = session.start_time ? new Date(session.start_time).toLocaleTimeString() : '--';
        const statusClass = session.status === 'active' ? 'safe' : session.status === 'paused' ? 'review' : 'suspicious';

        return `<tr>
            <td><code style="color:var(--accent-blue);font-size:0.8rem;">${escapeHtml((session.id || '').slice(0, 8))}...</code></td>
            <td>${escapeHtml(session.name || session.exam_name || 'Exam Session')}</td>
            <td><span class="badge badge-${statusClass}">${(session.status || 'active').toUpperCase()}</span></td>
            <td>${sessionStudents.length}</td>
            <td>${started}</td>
            <td>${session.duration || '--'}</td>
            <td><span class="${getRiskClass(avgRisk)}">${avgRisk}%</span></td>
            <td><button class="btn-details" onclick="viewSessionDetail('${session.id}')"><i class="fas fa-eye"></i> View</button></td>
        </tr>`;
    }).join('');

    if (resultsEl) resultsEl.textContent = `Showing ${sessions.length} sessions`;
}

function populateStudentsView() {
    const tbody = document.getElementById('studentsDirectoryBody');
    if (!tbody) return;

    const students = State.students;
    const totalEl = document.getElementById('studentsTotal');
    const onlineEl = document.getElementById('studentsOnline');
    const flaggedEl = document.getElementById('studentsFlagged');
    const avgEl = document.getElementById('studentsAvgScore');
    const resultsEl = document.getElementById('studentsResultsCount');

    if (totalEl) totalEl.textContent = students.length;
    if (onlineEl) onlineEl.textContent = students.length;
    if (flaggedEl) flaggedEl.textContent = students.filter(s => (s.risk_score || 0) > 60).length;
    if (avgEl) {
        const avg = students.length
            ? Math.round(students.reduce((a, s) => a + (s.risk_score || 0), 0) / students.length)
            : 0;
        avgEl.textContent = avg;
    }

    if (students.length === 0) {
        tbody.innerHTML = `<tr class="loading-row"><td colspan="8"><div class="loading-spinner"><i class="fas fa-inbox"></i><span>No students found</span></div></td></tr>`;
        if (resultsEl) resultsEl.textContent = 'Showing 0 students';
        return;
    }

    tbody.innerHTML = students.map(student => {
        const status = getRiskStatus(student.risk_score);
        const riskClass = getRiskClass(student.risk_score);
        const initials = getInitials(student.name);

        return `<tr>
            <td>
                <div class="student-cell">
                    <div class="student-avatar">${initials}</div>
                    <span class="student-name">${escapeHtml(student.name)}</span>
                </div>
            </td>
            <td><span style="color:var(--text-muted);font-size:0.85rem;">${escapeHtml(student.email)}</span></td>
            <td><span class="badge badge-${status}">${status.toUpperCase()}</span></td>
            <td><span class="${riskClass}" style="font-weight:600;">${Math.round(student.risk_score)}%</span></td>
            <td>${Math.round(student.engagement_score || 0)}%</td>
            <td>1</td>
            <td>${new Date().toLocaleTimeString()}</td>
            <td>
                <button class="btn-details" style="margin-right:4px;" onclick="viewStudentDetails('${student.student_id || student.id}')">
                    <i class="fas fa-eye"></i> View
                </button>
                <button class="btn-details" style="background-color:var(--bg-secondary);color:var(--accent-yellow);border-color:var(--accent-yellow);" onclick="warnStudent('${student.student_id || student.id}')">
                    <i class="fas fa-exclamation-triangle"></i> Warn
                </button>
            </td>
        </tr>`;
    }).join('');

    if (resultsEl) resultsEl.textContent = `Showing ${students.length} students`;
}

function populateAlertsView() {
    const tbody = document.getElementById('alertsTableBody');
    if (!tbody) return;

    const alerts = State.activities.filter(a => a.type === 'danger' || a.type === 'warning');
    const totalEl = document.getElementById('alertsTotalCount');
    const criticalEl = document.getElementById('alertsCriticalCount');
    const resultsEl = document.getElementById('alertsResultsCount');

    if (totalEl) totalEl.textContent = alerts.length;
    if (criticalEl) criticalEl.textContent = alerts.filter(a => a.type === 'danger').length;

    if (alerts.length === 0) {
        tbody.innerHTML = `<tr class="loading-row"><td colspan="7"><div class="loading-spinner"><i class="fas fa-inbox"></i><span>No alerts recorded</span></div></td></tr>`;
        if (resultsEl) resultsEl.textContent = 'Showing 0 alerts';
        return;
    }

    tbody.innerHTML = alerts.map(alert => {
        const severity = alert.type === 'danger' ? 'suspicious' : 'review';
        const time = alert.timestamp ? formatTime(alert.timestamp) : '--';

        return `<tr>
            <td style="font-size:0.85rem;color:var(--text-muted);">${time}</td>
            <td><span class="badge badge-${severity}">${alert.type === 'danger' ? 'CRITICAL' : 'WARNING'}</span></td>
            <td>${escapeHtml(alert.title)}</td>
            <td>${escapeHtml(alert.description)}</td>
            <td>--</td>
            <td style="font-size:0.85rem;">${escapeHtml(alert.title)}</td>
            <td><button class="btn-details" onclick="dismissAlert()"><i class="fas fa-check"></i> Dismiss</button></td>
        </tr>`;
    }).join('');

    if (resultsEl) resultsEl.textContent = `Showing ${alerts.length} alerts`;
}

function viewSessionDetail(sessionId) {
    showToast({ type: 'info', title: 'Session Details', message: `Viewing session ${sessionId.slice(0, 8)}...` });
}

function createNewSession() {
    const name = prompt('Enter exam name:');
    if (name) {
        showToast({ type: 'success', title: 'Session Created', message: `New session "${name}" has been created` });
    }
}

function clearAllAlerts() {
    showToast({ type: 'success', title: 'Alerts Cleared', message: 'All alerts marked as read' });
}

function dismissAlert() {
    showToast({ type: 'info', title: 'Alert Dismissed', message: 'Alert has been dismissed' });
}

function generateBatchReport() {
    showToast({ type: 'info', title: 'Generating Report', message: 'Batch report is being generated...' });
}

window.viewSessionDetail = viewSessionDetail;
window.createNewSession = createNewSession;
window.clearAllAlerts = clearAllAlerts;
window.dismissAlert = dismissAlert;
window.generateBatchReport = generateBatchReport;

// =============================================================================
// Utilities
// =============================================================================
function updateTime() {
    if (Elements.currentTime) {
        Elements.currentTime.textContent = new Date().toLocaleTimeString();
    }
}

function getRiskStatus(score) {
    if (score > 60) return 'suspicious';
    if (score > 30) return 'review';
    return 'safe';
}

function getRiskClass(score) {
    if (score > 60) return 'risk-high';
    if (score > 30) return 'risk-medium';
    return 'risk-low';
}

function getInitials(name) {
    return (name || 'U')
        .split(' ')
        .map(n => n[0])
        .join('')
        .toUpperCase()
        .slice(0, 2);
}

function getAlertIcon(eventType) {
    const icons = {
        'face_missing': 'fa-user-slash',
        'multiple_faces': 'fa-users',
        'tab_switch': 'fa-window-restore',
        'copy_paste': 'fa-clipboard',
        'plagiarism_detected': 'fa-copy',
        'unusual_behavior': 'fa-exclamation-triangle',
    };
    return icons[eventType] || 'fa-bell';
}

function formatEventType(type) {
    return type
        .split('_')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
}

function formatTime(date) {
    const now = new Date();
    const diff = (now - date) / 1000;

    if (diff < 60) return 'Just now';
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return date.toLocaleDateString();
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text || '';
    return div.innerHTML;
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

// =============================================================================
// Export Functions
// =============================================================================
function exportData() {
    const students = filterStudents(State.students);

    const headers = ['Name', 'Email', 'Status', 'Risk Score', 'Engagement', 'Effort'];
    const rows = students.map(s => [
        s.name,
        s.email,
        getRiskStatus(s.risk_score),
        Math.round(s.risk_score),
        Math.round(s.engagement_score || 0),
        Math.round(s.effort_alignment || 0),
    ]);

    const csv = [
        headers.join(','),
        ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
    ].join('\n');

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `examguard-report-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);

    showToast({
        type: 'success',
        title: 'Export Complete',
        message: `Exported ${students.length} students to CSV`,
    });
}

function generateStudentReport() {
    showToast({
        type: 'info',
        title: 'Generating Report',
        message: 'PDF report is being generated...',
    });
}

window.exportData = exportData;
window.fetchData = fetchStudentData;
window.generateStudentReport = generateStudentReport;
