import { useState, useEffect, useMemo } from 'react';
import { getRiskStatus, getRiskClass } from '../utils';
import { fetchVisitedSites, fetchSessionEvents } from '../hooks/api';

const CATEGORY_CONFIG = {
  AI: { color: '#ef4444', icon: 'fa-robot', bg: 'rgba(239,68,68,0.12)' },
  CHEATING: { color: '#dc2626', icon: 'fa-user-secret', bg: 'rgba(220,38,38,0.12)' },
  ENTERTAINMENT: { color: '#f59e0b', icon: 'fa-film', bg: 'rgba(245,158,11,0.12)' },
  Forbidden: { color: '#ef4444', icon: 'fa-ban', bg: 'rgba(239,68,68,0.12)' },
  General: { color: '#6b7280', icon: 'fa-globe', bg: 'rgba(107,114,128,0.12)' },
  EXAM: { color: '#10b981', icon: 'fa-graduation-cap', bg: 'rgba(16,185,129,0.12)' },
  OTHER: { color: '#6b7280', icon: 'fa-link', bg: 'rgba(107,114,128,0.12)' },
};

const EVENT_CONFIG = {
  TAB_SWITCH: { icon: 'fa-window-restore', color: '#f59e0b', label: 'Tab Switch' },
  NAVIGATION: { icon: 'fa-compass', color: '#3b82f6', label: 'Navigation' },
  FORBIDDEN_SITE: { icon: 'fa-ban', color: '#ef4444', label: 'Forbidden Site' },
  FORBIDDEN_CONTENT: { icon: 'fa-exclamation-circle', color: '#dc2626', label: 'Forbidden Content' },
  COPY: { icon: 'fa-copy', color: '#8b5cf6', label: 'Copy' },
  PASTE: { icon: 'fa-paste', color: '#7c3aed', label: 'Paste' },
  CUT: { icon: 'fa-cut', color: '#6d28d9', label: 'Cut' },
  FACE_ABSENT: { icon: 'fa-user-slash', color: '#ef4444', label: 'Face Absent' },
  WINDOW_BLUR: { icon: 'fa-eye-slash', color: '#f97316', label: 'Window Blur' },
  WINDOW_FOCUS: { icon: 'fa-eye', color: '#10b981', label: 'Window Focus' },
  FULLSCREEN_EXIT: { icon: 'fa-compress', color: '#f97316', label: 'Exited Fullscreen' },
  TAB_CREATED: { icon: 'fa-plus-circle', color: '#06b6d4', label: 'New Tab Opened' },
  TAB_CLOSED: { icon: 'fa-minus-circle', color: '#64748b', label: 'Tab Closed' },
  TAB_AUDIT: { icon: 'fa-search', color: '#8b5cf6', label: 'Tab Audit' },
  BROWSING_SUMMARY: { icon: 'fa-chart-pie', color: '#3b82f6', label: 'Browsing Summary' },
  PHONE_DETECTED: { icon: 'fa-mobile-alt', color: '#dc2626', label: 'Phone Detected' },
  TRANSFORMER_ALERT: { icon: 'fa-brain', color: '#ef4444', label: 'AI Similarity Alert' },
  CROSS_COMPARE_ALERT: { icon: 'fa-clone', color: '#f59e0b', label: 'Cross-Compare Alert' },
  TYPING: { icon: 'fa-keyboard', color: '#64748b', label: 'Typing' },
  CLICK: { icon: 'fa-mouse-pointer', color: '#94a3b8', label: 'Click' },
  VISIBILITY_CHANGE: { icon: 'fa-low-vision', color: '#f97316', label: 'Visibility Change' },
};

export default function StudentModal({ student, onClose }) {
  const [activeTab, setActiveTab] = useState('overview');
  const [visitedSites, setVisitedSites] = useState(null);
  const [events, setEvents] = useState(null);
  const [loading, setLoading] = useState({});
  const [eventFilter, setEventFilter] = useState('all');

  const sessionId = student?.session_id || student?.latest_session_id;

  // Load data on tab switch
  useEffect(() => {
    if (!sessionId) return;

    if (activeTab === 'overview' || activeTab === 'browsing') {
      if (!visitedSites) {
        setLoading(l => ({ ...l, sites: true }));
        fetchVisitedSites(sessionId)
          .then(setVisitedSites)
          .catch(() => setVisitedSites({ sites: [], flagged_count: 0, category_breakdown: {} }))
          .finally(() => setLoading(l => ({ ...l, sites: false })));
      }
    }

    if (activeTab === 'timeline' || activeTab === 'overview') {
      if (!events) {
        setLoading(l => ({ ...l, events: true }));
        fetchSessionEvents(sessionId)
          .then(setEvents)
          .catch(() => setEvents({ events: [] }))
          .finally(() => setLoading(l => ({ ...l, events: false })));
      }
    }
  }, [activeTab, sessionId]);

  // Derived data
  const actionSummary = useMemo(() => {
    if (!events?.events) return {};
    const counts = {};
    for (const e of events.events) {
      const t = e.event_type;
      counts[t] = (counts[t] || 0) + 1;
    }
    return counts;
  }, [events]);

  const browsingSummary = useMemo(() => {
    if (!events?.events) return null;
    const summaries = events.events.filter(e => e.event_type === 'BROWSING_SUMMARY' && e.data);
    if (summaries.length === 0) return null;
    return summaries[0].data;
  }, [events]);

  const filteredEvents = useMemo(() => {
    if (!events?.events) return [];
    let list = events.events;
    if (eventFilter !== 'all') {
      list = list.filter(e => e.event_type === eventFilter);
    }
    return list.filter(e => !['TYPING', 'CLICK'].includes(e.event_type));
  }, [events, eventFilter]);

  const riskEvents = useMemo(() => {
    if (!events?.events) return [];
    return events.events.filter(e =>
      ['FORBIDDEN_SITE', 'FORBIDDEN_CONTENT', 'FACE_ABSENT', 'PHONE_DETECTED',
        'TRANSFORMER_ALERT', 'CROSS_COMPARE_ALERT', 'TAB_AUDIT', 'FULLSCREEN_EXIT'].includes(e.event_type)
    );
  }, [events]);

  if (!student) return null;

  const status = getRiskStatus(student.risk_score);

  const tabs = [
    { id: 'overview', label: 'Overview', icon: 'fa-th-large' },
    { id: 'timeline', label: 'Activity', icon: 'fa-stream' },
    { id: 'browsing', label: 'Browsing', icon: 'fa-globe' },
    { id: 'risks', label: 'Risks', icon: 'fa-shield-alt' },
  ];

  return (
    <div className="modal active">
      <div className="modal-backdrop" onClick={onClose}></div>
      <div className="modal-content student-modal-wide">
        {/* Header */}
        <div className="modal-header student-modal-header">
          <div className="smh-left">
            <div className={`smh-avatar ${status}`}>
              {(student.name || 'U').split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)}
            </div>
            <div className="smh-info">
              <h3>{student.name}</h3>
              <span className="smh-meta">
                {student.email && <span>{student.email}</span>}
                {student.student_id && <span> &middot; ID: {student.student_id}</span>}
              </span>
            </div>
          </div>
          <div className="smh-right">
            <div className={`smh-risk-badge ${status}`}>
              <i className={`fas ${status === 'suspicious' ? 'fa-exclamation-triangle' : status === 'review' ? 'fa-eye' : 'fa-check-circle'}`}></i>
              {Math.round(student.risk_score)}% Risk
            </div>
            <button className="modal-close" onClick={onClose}><i className="fas fa-times"></i></button>
          </div>
        </div>

        {/* Tab Bar */}
        <div className="sm-tabs">
          {tabs.map(tab => (
            <button
              key={tab.id}
              className={`sm-tab ${activeTab === tab.id ? 'active' : ''}`}
              onClick={() => setActiveTab(tab.id)}
            >
              <i className={`fas ${tab.icon}`}></i>
              <span>{tab.label}</span>
              {tab.id === 'risks' && riskEvents.length > 0 && (
                <span className="sm-tab-badge">{riskEvents.length}</span>
              )}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="modal-body sm-body">
          {activeTab === 'overview' && (
            <OverviewTab
              student={student}
              actionSummary={actionSummary}
              browsingSummary={browsingSummary}
              visitedSites={visitedSites}
              riskEvents={riskEvents}
              loading={loading}
            />
          )}
          {activeTab === 'timeline' && (
            <TimelineTab
              events={filteredEvents}
              eventFilter={eventFilter}
              setEventFilter={setEventFilter}
              actionSummary={actionSummary}
              loading={loading.events}
            />
          )}
          {activeTab === 'browsing' && (
            <BrowsingTab
              visitedSites={visitedSites}
              browsingSummary={browsingSummary}
              loading={loading.sites}
            />
          )}
          {activeTab === 'risks' && (
            <RisksTab
              student={student}
              riskEvents={riskEvents}
              browsingSummary={browsingSummary}
              loading={loading.events}
            />
          )}
        </div>

        {/* Footer */}
        <div className="modal-footer">
          <span className="sm-session-id">
            <i className="fas fa-fingerprint"></i> {sessionId ? sessionId.substring(0, 12) : 'No session'}
          </span>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button className="btn btn-secondary" onClick={onClose}>Close</button>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ==================== OVERVIEW TAB ==================== */
function OverviewTab({ student, actionSummary, browsingSummary, visitedSites, riskEvents, loading }) {
  const status = getRiskStatus(student.risk_score);

  return (
    <div className="sm-overview">
      {/* Score Cards */}
      <div className="sm-score-grid">
        <ScoreCard label="Risk Score" value={Math.round(student.risk_score)} max={100}
          color={student.risk_score > 60 ? '#ef4444' : student.risk_score > 30 ? '#f59e0b' : '#10b981'}
          icon="fa-shield-alt" suffix="%" />
        <ScoreCard label="Engagement" value={Math.round(student.engagement_score || 0)} max={100}
          color="#3b82f6" icon="fa-eye" suffix="%" />
        <ScoreCard label="Effort" value={Math.round(student.effort_alignment || 0)} max={100}
          color="#8b5cf6" icon="fa-chart-bar" suffix="%" />
        <ScoreCard label="Relevance" value={Math.round(student.content_relevance || 0)} max={100}
          color="#06b6d4" icon="fa-bullseye" suffix="%" />
      </div>

      {/* Quick Action Counts */}
      <div className="sm-section">
        <h4 className="sm-section-title"><i className="fas fa-bolt"></i> Actions Summary</h4>
        <div className="sm-action-grid">
          <ActionBadge icon="fa-window-restore" label="Tab Switches" count={student.tab_switch_count || 0} color="#f59e0b" />
          <ActionBadge icon="fa-copy" label="Copy/Paste" count={student.copy_count || 0} color="#8b5cf6" />
          <ActionBadge icon="fa-ban" label="Flagged Sites" count={student.forbidden_site_count || 0} color="#ef4444" />
          <ActionBadge icon="fa-compass" label="Navigations" count={actionSummary.NAVIGATION || 0} color="#3b82f6" />
          <ActionBadge icon="fa-user-slash" label="Face Absent" count={actionSummary.FACE_ABSENT || 0} color="#f97316" />
          <ActionBadge icon="fa-eye-slash" label="Window Blur" count={actionSummary.WINDOW_BLUR || 0} color="#f97316" />
          <ActionBadge icon="fa-plus-circle" label="Tabs Opened" count={actionSummary.TAB_CREATED || 0} color="#06b6d4" />
          <ActionBadge icon="fa-compress" label="Fullscreen Exit" count={actionSummary.FULLSCREEN_EXIT || 0} color="#dc2626" />
        </div>
      </div>

      {/* Browsing Summary - time breakdown */}
      {browsingSummary && (
        <div className="sm-section">
          <h4 className="sm-section-title"><i className="fas fa-clock"></i> Time Distribution</h4>
          <TimeBreakdownBar data={browsingSummary.timeByCategory} total={browsingSummary.totalTime || 1} />
          <div className="sm-time-stats">
            <span className="sm-time-stat exam"><i className="fas fa-check-circle"></i> Exam: {browsingSummary.examTimePercent || 0}%</span>
            <span className="sm-time-stat distraction"><i className="fas fa-exclamation-triangle"></i> Distraction: {browsingSummary.distractionTimePercent || 0}%</span>
          </div>
        </div>
      )}

      {/* Recent Risk Events */}
      {riskEvents.length > 0 && (
        <div className="sm-section">
          <h4 className="sm-section-title">
            <i className="fas fa-exclamation-circle"></i> Recent Alerts
            <span className="sm-count-badge danger">{riskEvents.length}</span>
          </h4>
          <div className="sm-risk-list">
            {riskEvents.slice(0, 5).map((evt, i) => (
              <EventItem key={evt.id || i} event={evt} compact />
            ))}
            {riskEvents.length > 5 && (
              <div className="sm-see-more">+{riskEvents.length - 5} more alerts</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

/* ==================== TIMELINE TAB ==================== */
function TimelineTab({ events, eventFilter, setEventFilter, actionSummary, loading }) {
  const eventTypes = Object.keys(actionSummary).filter(t => !['TYPING', 'CLICK'].includes(t));

  return (
    <div className="sm-timeline-tab">
      {/* Filter Bar */}
      <div className="sm-filter-bar">
        <select className="sm-filter-select" value={eventFilter} onChange={e => setEventFilter(e.target.value)}>
          <option value="all">All Events</option>
          {eventTypes.sort().map(t => (
            <option key={t} value={t}>
              {EVENT_CONFIG[t]?.label || t} ({actionSummary[t]})
            </option>
          ))}
        </select>
        <span className="sm-filter-count">{events.length} events</span>
      </div>

      {/* Event List */}
      <div className="sm-event-list">
        {loading ? (
          <div className="sm-loading"><i className="fas fa-spinner fa-spin"></i> Loading activity...</div>
        ) : events.length === 0 ? (
          <div className="sm-empty"><i className="fas fa-inbox"></i> No events recorded</div>
        ) : (
          events.map((evt, i) => <EventItem key={evt.id || i} event={evt} />)
        )}
      </div>
    </div>
  );
}

/* ==================== BROWSING TAB ==================== */
function BrowsingTab({ visitedSites, browsingSummary, loading }) {
  return (
    <div className="sm-browsing-tab">
      {/* Browsing Risk Overview */}
      {browsingSummary && (
        <div className="sm-section">
          <h4 className="sm-section-title"><i className="fas fa-chart-pie"></i> Browsing Analysis</h4>
          <div className="sm-browse-scores">
            <div className="sm-browse-score-item">
              <span className="sm-bsi-label">Browsing Risk</span>
              <div className="sm-bsi-bar">
                <div className="sm-bsi-fill" style={{
                  width: `${browsingSummary.browsingRiskScore || 0}%`,
                  background: (browsingSummary.browsingRiskScore || 0) > 60 ? '#ef4444' :
                    (browsingSummary.browsingRiskScore || 0) > 30 ? '#f59e0b' : '#10b981',
                }} />
              </div>
              <span className="sm-bsi-value">{browsingSummary.browsingRiskScore || 0}</span>
            </div>
            <div className="sm-browse-score-item">
              <span className="sm-bsi-label">Effort Score</span>
              <div className="sm-bsi-bar">
                <div className="sm-bsi-fill" style={{
                  width: `${browsingSummary.effortScore || 0}%`,
                  background: (browsingSummary.effortScore || 0) > 70 ? '#10b981' :
                    (browsingSummary.effortScore || 0) > 40 ? '#f59e0b' : '#ef4444',
                }} />
              </div>
              <span className="sm-bsi-value">{browsingSummary.effortScore || 0}</span>
            </div>
          </div>
          <div className="sm-browse-meta">
            <span><i className="fas fa-globe"></i> {browsingSummary.uniqueSitesVisited || 0} sites</span>
            <span><i className="fas fa-flag"></i> {browsingSummary.flaggedSitesCount || 0} flagged</span>
            <span><i className="fas fa-window-restore"></i> {browsingSummary.openTabsCount || 0} tabs open</span>
            <span><i className="fas fa-exclamation-triangle"></i> {browsingSummary.flaggedOpenTabs || 0} flagged tabs</span>
          </div>
          <div style={{ marginTop: '1rem' }}>
            <TimeBreakdownBar data={browsingSummary.timeByCategory} total={browsingSummary.totalTime || 1} />
          </div>
        </div>
      )}

      {/* Category Breakdown */}
      {visitedSites?.category_breakdown && Object.keys(visitedSites.category_breakdown).length > 0 && (
        <div className="sm-section">
          <h4 className="sm-section-title"><i className="fas fa-tags"></i> Categories</h4>
          <div className="sm-category-chips">
            {Object.entries(visitedSites.category_breakdown).map(([cat, count]) => {
              const cfg = CATEGORY_CONFIG[cat] || CATEGORY_CONFIG.General;
              return (
                <span key={cat} className="sm-category-chip" style={{ background: cfg.bg, color: cfg.color }}>
                  <i className={`fas ${cfg.icon}`}></i> {cat}: {count}
                </span>
              );
            })}
          </div>
        </div>
      )}

      {/* Sites List */}
      <div className="sm-section">
        <h4 className="sm-section-title">
          <i className="fas fa-list"></i> Visited Sites
          {visitedSites && <span className="sm-count-badge">{visitedSites.total_sites || visitedSites.sites?.length || 0}</span>}
          {visitedSites?.flagged_count > 0 && (
            <span className="sm-count-badge danger">{visitedSites.flagged_count} flagged</span>
          )}
        </h4>
        {loading ? (
          <div className="sm-loading"><i className="fas fa-spinner fa-spin"></i> Loading...</div>
        ) : visitedSites?.sites?.length > 0 ? (
          <div className="sm-sites-list">
            {visitedSites.sites.map((site, idx) => {
              const cfg = CATEGORY_CONFIG[site.category] || CATEGORY_CONFIG.General;
              return (
                <div key={idx} className={`sm-site-item ${site.is_flagged ? 'flagged' : ''}`}>
                  <i className={`fas ${cfg.icon}`} style={{ color: cfg.color }}></i>
                  <div className="sm-site-info">
                    <span className="sm-site-title" style={site.is_flagged ? { color: cfg.color, fontWeight: 600 } : {}}>
                      {site.title || site.url}
                    </span>
                    <span className="sm-site-url">{site.url}</span>
                  </div>
                  <span className="sm-site-badge" style={{ background: cfg.bg, color: cfg.color }}>
                    {site.category}
                  </span>
                  <span className="sm-site-time">
                    {site.timestamp ? new Date(site.timestamp).toLocaleTimeString() : ''}
                  </span>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="sm-empty"><i className="fas fa-inbox"></i> No browsing data recorded</div>
        )}
      </div>
    </div>
  );
}

/* ==================== RISKS TAB ==================== */
function RisksTab({ student, riskEvents, browsingSummary, loading }) {
  const status = getRiskStatus(student.risk_score);

  const groupedRisks = useMemo(() => {
    const groups = {};
    for (const evt of riskEvents) {
      const t = evt.event_type;
      if (!groups[t]) groups[t] = [];
      groups[t].push(evt);
    }
    return groups;
  }, [riskEvents]);

  return (
    <div className="sm-risks-tab">
      {/* Risk Score Hero */}
      <div className={`sm-risk-hero ${status}`}>
        <div className="sm-risk-hero-score">
          <svg viewBox="0 0 120 120" className="sm-risk-circle">
            <circle cx="60" cy="60" r="52" fill="none" stroke="rgba(255,255,255,0.1)" strokeWidth="8" />
            <circle cx="60" cy="60" r="52" fill="none" stroke="currentColor" strokeWidth="8"
              strokeLinecap="round"
              strokeDasharray={`${(student.risk_score / 100) * 327} 327`}
              transform="rotate(-90 60 60)" />
          </svg>
          <div className="sm-risk-hero-value">{Math.round(student.risk_score)}%</div>
        </div>
        <div className="sm-risk-hero-info">
          <h4>Risk Level: {status.toUpperCase()}</h4>
          <p>
            {status === 'suspicious' ? 'Multiple risk indicators detected. Immediate review recommended.' :
              status === 'review' ? 'Some risk indicators found. Monitor this student closely.' :
                'No significant risk indicators. Student behavior appears normal.'}
          </p>
        </div>
      </div>

      {/* Risk Breakdown */}
      <div className="sm-section">
        <h4 className="sm-section-title"><i className="fas fa-chart-bar"></i> Score Breakdown</h4>
        <div className="sm-risk-bars">
          <RiskBar label="Engagement" value={student.engagement_score || 0} good />
          <RiskBar label="Effort Alignment" value={student.effort_alignment || 0} good />
          <RiskBar label="Content Relevance" value={student.content_relevance || 0} good />
          {browsingSummary && (
            <RiskBar label="Browsing Risk" value={browsingSummary.browsingRiskScore || 0} />
          )}
        </div>
      </div>

      {/* Risk Events by Type */}
      {Object.keys(groupedRisks).length > 0 ? (
        <div className="sm-section">
          <h4 className="sm-section-title">
            <i className="fas fa-exclamation-triangle"></i> Risk Events
            <span className="sm-count-badge danger">{riskEvents.length}</span>
          </h4>
          {Object.entries(groupedRisks).map(([type, evts]) => {
            const cfg = EVENT_CONFIG[type] || { icon: 'fa-bell', color: '#ef4444', label: type };
            return (
              <div key={type} className="sm-risk-group">
                <div className="sm-risk-group-header">
                  <i className={`fas ${cfg.icon}`} style={{ color: cfg.color }}></i>
                  <span>{cfg.label}</span>
                  <span className="sm-count-badge" style={{ background: `${cfg.color}20`, color: cfg.color }}>{evts.length}</span>
                </div>
                <div className="sm-risk-group-items">
                  {evts.slice(0, 3).map((evt, i) => (
                    <EventItem key={evt.id || i} event={evt} compact />
                  ))}
                  {evts.length > 3 && <div className="sm-see-more">+{evts.length - 3} more</div>}
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="sm-section">
          <div className="sm-empty success">
            <i className="fas fa-check-circle"></i>
            <p>No risk events detected</p>
          </div>
        </div>
      )}
    </div>
  );
}

/* ==================== REUSABLE COMPONENTS ==================== */

function ScoreCard({ label, value, max, color, icon, suffix = '' }) {
  const pct = Math.min((value / max) * 100, 100);
  return (
    <div className="sm-score-card">
      <div className="sm-sc-header">
        <i className={`fas ${icon}`} style={{ color }}></i>
        <span>{label}</span>
      </div>
      <div className="sm-sc-value" style={{ color }}>{value}{suffix}</div>
      <div className="sm-sc-bar">
        <div className="sm-sc-fill" style={{ width: `${pct}%`, background: color }}></div>
      </div>
    </div>
  );
}

function ActionBadge({ icon, label, count, color }) {
  return (
    <div className="sm-action-badge" style={{ borderColor: count > 0 ? `${color}40` : 'var(--border-color)' }}>
      <i className={`fas ${icon}`} style={{ color: count > 0 ? color : 'var(--text-muted)' }}></i>
      <span className="sm-ab-count" style={count > 0 ? { color } : {}}>{count}</span>
      <span className="sm-ab-label">{label}</span>
    </div>
  );
}

function EventItem({ event, compact = false }) {
  const cfg = EVENT_CONFIG[event.event_type] || { icon: 'fa-circle', color: '#64748b', label: event.event_type };
  const data = event.data || {};
  const time = event.timestamp ? new Date(event.timestamp).toLocaleTimeString() : '';

  let description = data.message || data.url || data.title || '';
  if (event.event_type === 'NAVIGATION') {
    description = `${data.action === 'TAB_SWITCH' ? 'Switched to' : 'Navigated to'}: ${data.title || data.url || 'unknown'}`;
  } else if (event.event_type === 'FORBIDDEN_SITE') {
    description = `[${data.category}] ${data.site || data.url || 'unknown'} — ${data.riskLevel || ''} risk`;
  } else if (event.event_type === 'TAB_AUDIT') {
    description = `${data.flaggedTabs || 0} flagged of ${data.totalTabs || 0} open tabs`;
  } else if (event.event_type === 'BROWSING_SUMMARY') {
    description = `Exam ${data.examTimePercent || 0}% | Distraction ${data.distractionTimePercent || 0}% | Risk ${data.browsingRiskScore || 0}`;
  } else if (event.event_type === 'TAB_CREATED') {
    description = `New tab: ${data.url || 'blank'}`;
  } else if (event.event_type === 'TAB_CLOSED') {
    description = data.wasFlagged ? `Closed flagged tab (${data.closedCategory})` : 'Tab closed';
  } else if (event.event_type === 'FACE_ABSENT') {
    description = `Face not detected (confidence: ${data.confidence || 'N/A'})`;
  } else if (event.event_type === 'TRANSFORMER_ALERT') {
    description = `Similarity: ${((data.similarity || 0) * 100).toFixed(1)}% — "${(data.text_preview || '').substring(0, 60)}"`;
  }

  return (
    <div className={`sm-event-item ${compact ? 'compact' : ''} ${event.risk_weight > 0 ? 'has-risk' : ''}`}>
      <div className="sm-ei-icon" style={{ color: cfg.color, background: `${cfg.color}15` }}>
        <i className={`fas ${cfg.icon}`}></i>
      </div>
      <div className="sm-ei-content">
        <span className="sm-ei-label">{cfg.label}</span>
        {description && <span className="sm-ei-desc">{description}</span>}
      </div>
      {event.risk_weight > 0 && (
        <span className="sm-ei-risk">+{event.risk_weight}</span>
      )}
      <span className="sm-ei-time">{time}</span>
    </div>
  );
}

function TimeBreakdownBar({ data, total }) {
  if (!data || total <= 0) return null;
  const segments = [
    { key: 'exam', label: 'Exam', color: '#10b981' },
    { key: 'other', label: 'Other', color: '#64748b' },
    { key: 'ai', label: 'AI', color: '#ef4444' },
    { key: 'cheating', label: 'Cheating', color: '#dc2626' },
    { key: 'entertainment', label: 'Entertainment', color: '#f59e0b' },
  ];

  return (
    <div className="sm-time-breakdown">
      <div className="sm-tb-bar">
        {segments.map(seg => {
          const val = data[seg.key] || 0;
          const pct = (val / total) * 100;
          if (pct < 0.5) return null;
          return (
            <div key={seg.key} className="sm-tb-segment"
              style={{ width: `${pct}%`, background: seg.color }}
              title={`${seg.label}: ${Math.round(pct)}% (${Math.round(val / 1000)}s)`} />
          );
        })}
      </div>
      <div className="sm-tb-legend">
        {segments.map(seg => {
          const val = data[seg.key] || 0;
          const pct = Math.round((val / total) * 100);
          if (pct < 1) return null;
          return (
            <span key={seg.key} className="sm-tb-legend-item">
              <span className="sm-tb-dot" style={{ background: seg.color }}></span>
              {seg.label} {pct}%
            </span>
          );
        })}
      </div>
    </div>
  );
}

function RiskBar({ label, value, good = false }) {
  const v = Math.round(value);
  const color = good
    ? (v > 70 ? '#10b981' : v > 40 ? '#f59e0b' : '#ef4444')
    : (v > 60 ? '#ef4444' : v > 30 ? '#f59e0b' : '#10b981');
  return (
    <div className="sm-risk-bar-row">
      <span className="sm-rb-label">{label}</span>
      <div className="sm-rb-track">
        <div className="sm-rb-fill" style={{ width: `${v}%`, background: color }}></div>
      </div>
      <span className="sm-rb-value" style={{ color }}>{v}%</span>
    </div>
  );
}
