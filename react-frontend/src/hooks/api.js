import { API_BASE } from '../config';

// Fetch all students / dashboard data
export async function fetchStudents() {
  const res = await fetch(`${API_BASE}/analysis/dashboard`);
  if (!res.ok) throw new Error('Failed to fetch students');
  return res.json();
}

// Fetch all sessions
export async function fetchSessions() {
  const res = await fetch(`${API_BASE}/sessions`);
  if (!res.ok) throw new Error('Failed to fetch sessions');
  return res.json();
}

// Start a new session
export async function startSession(payload) {
  const res = await fetch(`${API_BASE}/sessions/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error('Failed to start session');
  return res.json();
}

// End a session
export async function endSession(sessionId) {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}/end`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('Failed to end session');
  return res.json();
}

// Log a single event
export async function logEvent(payload) {
  const res = await fetch(`${API_BASE}/events/log`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error('Failed to log event');
  return res.json();
}

// Get session report summary
export async function getReportSummary(sessionId) {
  const res = await fetch(`${API_BASE}/reports/session/${sessionId}/summary`);
  if (!res.ok) throw new Error('Failed to fetch report');
  return res.json();
}

// Download PDF report
export function getReportDownloadUrl(sessionId) {
  return `${API_BASE}/reports/session/${sessionId}/download`;
}

// Health check
export async function healthCheck() {
  const res = await fetch('http://localhost:8000/health');
  if (!res.ok) throw new Error('Health check failed');
  return res.json();
}

// Transformer status
export async function getTransformerStatus() {
  const res = await fetch(`${API_BASE}/analysis/transformer/status`);
  if (!res.ok) throw new Error('Failed to fetch transformer status');
  return res.json();
}

// Pipeline stats
export async function getPipelineStats() {
  const res = await fetch(`${API_BASE}/pipeline/stats`);
  if (!res.ok) throw new Error('Failed to fetch pipeline stats');
  return res.json();
}

// Fetch visited websites for a session
export async function fetchVisitedSites(sessionId) {
  const res = await fetch(`${API_BASE}/events/session/${sessionId}/visited-sites`);
  if (!res.ok) throw new Error('Failed to fetch visited sites');
  return res.json();
}

// Fetch events for a session (with optional type filter)
export async function fetchSessionEvents(sessionId, eventType = null) {
  let url = `${API_BASE}/events/session/${sessionId}?limit=200`;
  if (eventType) url += `&event_type=${eventType}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('Failed to fetch events');
  return res.json();
}

// Fetch event timeline for a session
export async function fetchSessionTimeline(sessionId) {
  const res = await fetch(`${API_BASE}/events/session/${sessionId}/timeline`);
  if (!res.ok) throw new Error('Failed to fetch timeline');
  return res.json();
}

// Fetch analysis results for a session
export async function fetchAnalysisResults(sessionId) {
  const res = await fetch(`${API_BASE}/analysis/student/${sessionId}`);
  if (!res.ok) throw new Error('Failed to fetch analysis');
  return res.json();
}

// Fetch detailed student info with sessions
export async function fetchStudentDetails(studentId) {
  const res = await fetch(`${API_BASE}/analysis/student/${studentId}`);
  if (!res.ok) throw new Error('Failed to fetch student details');
  return res.json();
}

// Fetch dashboard stats
export async function fetchDashboardStats() {
  const res = await fetch(`${API_BASE}/analysis/stats`);
  if (!res.ok) throw new Error('Failed to fetch dashboard stats');
  return res.json();
}
