import { useState, useMemo } from 'react';
import { useApp } from '../context/AppContext';
import { getRiskStatus, getRiskClass, getInitials, formatTime, exportCSV } from '../utils';
import Header from '../components/Header';
import StudentModal from '../components/StudentModal';

export default function Dashboard() {
  const { state, dispatch, loadStudents } = useApp();
  const [statusFilter, setStatusFilter] = useState('all');
  const [sessionFilter, setSessionFilter] = useState('all');
  const [search, setSearch] = useState('');
  const [sortField, setSortField] = useState('risk_score');
  const [sortDir, setSortDir] = useState('desc');
  const [selectedStudent, setSelectedStudent] = useState(null);

  const students = useMemo(() => {
    let filtered = state.students.filter(s => {
      if (search) {
        const q = search.toLowerCase();
        if (!s.name?.toLowerCase().includes(q) && !s.email?.toLowerCase().includes(q)) return false;
      }
      if (statusFilter !== 'all' && getRiskStatus(s.risk_score) !== statusFilter) return false;
      if (sessionFilter !== 'all' && s.session_id !== sessionFilter) return false;
      return true;
    });
    filtered.sort((a, b) => {
      let av = a[sortField], bv = b[sortField];
      if (typeof av === 'string') { av = av.toLowerCase(); bv = bv.toLowerCase(); }
      return sortDir === 'asc' ? (av > bv ? 1 : -1) : (av < bv ? 1 : -1);
    });
    return filtered;
  }, [state.students, statusFilter, sessionFilter, search, sortField, sortDir]);

  const stats = useMemo(() => {
    const all = state.students;
    const highRisk = all.filter(s => (s.risk_score || 0) > 60).length;
    const avgEng = all.length ? Math.round(all.reduce((a, s) => a + (s.engagement_score || 0), 0) / all.length) : 0;
    const avgEff = all.length ? Math.round(all.reduce((a, s) => a + (s.effort_alignment || 0), 0) / all.length) : 0;
    const safe = all.filter(s => getRiskStatus(s.risk_score) === 'safe').length;
    const review = all.filter(s => getRiskStatus(s.risk_score) === 'review').length;
    const suspicious = all.filter(s => getRiskStatus(s.risk_score) === 'suspicious').length;
    return { total: all.length, highRisk, avgEng, avgEff, safe, review, suspicious };
  }, [state.students]);

  function handleSort(field) {
    if (sortField === field) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortField(field); setSortDir('desc'); }
  }

  function notify(type, title, message) {
    dispatch({ type: 'ADD_TOAST', payload: { type, title, message } });
  }

  return (
    <>
      <Header title="Live Monitoring" />
      <div className="dashboard-content">
        {/* Stats Row */}
        <section className="stats-row">
          <StatCard icon="fa-users" color="blue" value={stats.total} label="Active Students" trend="+12%" up />
          <StatCard icon="fa-exclamation-triangle" color="red" value={stats.highRisk} label="High Risk Alerts" trend="-3%" />
          <StatCard icon="fa-eye" color="green" value={`${stats.avgEng}%`} label="Avg Engagement" trend="+5%" up />
          <StatCard icon="fa-chart-bar" color="purple" value={`${stats.avgEff}%`} label="Effort Alignment" trend="0%" neutral />
        </section>

        <div className="main-grid">
          {/* Student Table */}
          <section className="panel students-panel">
            <div className="panel-header">
              <h2><i className="fas fa-user-graduate"></i> Student Monitoring</h2>
              <div className="panel-actions">
                <div className="filter-group">
                  <select className="filter-select" value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>
                    <option value="all">All Status</option>
                    <option value="safe">Safe</option>
                    <option value="review">Review Needed</option>
                    <option value="suspicious">Suspicious</option>
                  </select>
                  <select className="filter-select" value={sessionFilter} onChange={e => setSessionFilter(e.target.value)}>
                    <option value="all">All Sessions</option>
                    {state.sessions.map(s => (
                      <option key={s.id} value={s.id}>{s.name || `Session ${s.id}`}</option>
                    ))}
                  </select>
                </div>
                <button className="btn btn-secondary" onClick={loadStudents}><i className="fas fa-sync-alt"></i></button>
                <button className="btn btn-primary" onClick={() => { exportCSV(students); notify('success', 'Export Complete', `Exported ${students.length} students`); }}><i className="fas fa-download"></i> Export</button>
              </div>
            </div>
            <div className="panel-header" style={{ borderBottom: 'none', paddingTop: 0 }}>
              <div className="search-box" style={{ maxWidth: 300 }}>
                <i className="fas fa-search"></i>
                <input type="text" placeholder="Filter students..." value={search} onChange={e => setSearch(e.target.value)} />
              </div>
            </div>
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th className="sortable" onClick={() => handleSort('name')}>Student <i className="fas fa-sort"></i></th>
                    <th className="sortable" onClick={() => handleSort('status')}>Status <i className="fas fa-sort"></i></th>
                    <th className="sortable" onClick={() => handleSort('risk_score')}>Risk <i className="fas fa-sort"></i></th>
                    <th>Active Site</th>
                    <th>Engagement</th>
                    <th>Effort</th>
                    <th className="sortable" onClick={() => handleSort('tab_switch_count')}>
                      <span title="Tab Switches"><i className="fas fa-window-restore"></i></span> <i className="fas fa-sort"></i>
                    </th>
                    <th className="sortable" onClick={() => handleSort('forbidden_site_count')}>
                      <span title="Flagged Sites"><i className="fas fa-ban"></i></span> <i className="fas fa-sort"></i>
                    </th>
                    <th className="sortable" onClick={() => handleSort('copy_count')}>
                      <span title="Copy/Paste"><i className="fas fa-copy"></i></span> <i className="fas fa-sort"></i>
                    </th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {students.length === 0 ? (
                    <tr className="loading-row">
                      <td colSpan="9">
                        <div className="loading-spinner"><i className="fas fa-inbox"></i><span>No students found</span></div>
                      </td>
                    </tr>
                  ) : students.map(student => {
                    const status = getRiskStatus(student.risk_score);
                    const riskClass = getRiskClass(student.risk_score);
                    const tabSwitches = student.tab_switch_count || 0;
                    const flaggedSites = student.forbidden_site_count || 0;
                    const copyCount = student.copy_count || 0;
                    return (
                      <tr key={student.student_id || student.id} className={status === 'suspicious' ? 'row-suspicious' : ''}>
                        <td>
                          <div className="student-cell">
                            <div className={`student-avatar avatar-${status}`}>{getInitials(student.name)}</div>
                            <div className="student-info">
                              <span className="student-name">{student.name}</span>
                              <span className="student-email">{student.email}</span>
                            </div>
                          </div>
                        </td>
                        <td><span className={`badge badge-${status}`}>{status.toUpperCase()}</span></td>
                        <td><span className={`risk-value ${riskClass}`}>{Math.round(student.risk_score)}</span></td>
                        <td>
                          <div className="active-site-cell" title={student.last_visited_url || 'No activity'}>
                            <span className="site-title">{student.last_visited_title || (student.last_visited_url ? new URL(student.last_visited_url).hostname : 'N/A')}</span>
                          </div>
                        </td>
                        <td>
                          <div className="progress-bar"><div className="progress-fill blue" style={{ width: `${student.engagement_score || 0}%` }}></div></div>
                          <span className="text-muted" style={{ fontSize: '0.75rem' }}>{Math.round(student.engagement_score || 0)}%</span>
                        </td>
                        <td>
                          <div className="progress-bar"><div className="progress-fill purple" style={{ width: `${student.effort_alignment || 0}%` }}></div></div>
                          <span className="text-muted" style={{ fontSize: '0.75rem' }}>{Math.round(student.effort_alignment || 0)}%</span>
                        </td>
                        <td>
                          <span className={`action-count ${tabSwitches > 5 ? 'warn' : tabSwitches > 10 ? 'danger' : ''}`} title="Tab Switches">
                            {tabSwitches}
                          </span>
                        </td>
                        <td>
                          <span className={`action-count ${flaggedSites > 0 ? 'danger' : ''}`} title="Flagged Sites">
                            {flaggedSites}
                          </span>
                        </td>
                        <td>
                          <span className={`action-count ${copyCount > 3 ? 'warn' : ''}`} title="Copy/Paste">
                            {copyCount}
                          </span>
                        </td>
                        <td>
                          <button className="btn-details" onClick={() => setSelectedStudent(student)}>
                            <i className="fas fa-eye"></i> View
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <div className="panel-footer">
              <span className="results-count">Showing <strong>{students.length}</strong> of <strong>{state.students.length}</strong> students</span>
            </div>
          </section>

          {/* Side Panels */}
          <aside className="side-panels">
            {/* Activity Feed */}
            <section className="panel activity-panel">
              <div className="panel-header">
                <h2><i className="fas fa-stream"></i> Live Activity</h2>
                <button className="btn-icon" title="Clear All" onClick={() => dispatch({ type: 'CLEAR_ACTIVITIES' })}>
                  <i className="fas fa-trash-alt"></i>
                </button>
              </div>
              <div className="activity-feed">
                {state.activities.length === 0 ? (
                  <div className="empty-state"><i className="fas fa-inbox"></i><p>No recent activity</p></div>
                ) : state.activities.slice(0, 10).map((a, i) => (
                  <div key={i} className="activity-item">
                    <div className={`activity-icon ${a.type}`}><i className={`fas ${a.icon}`}></i></div>
                    <div className="activity-content">
                      <div className="activity-title">{a.title}</div>
                      <div className="activity-desc">{a.description}</div>
                    </div>
                    <span className="activity-time">{formatTime(a.timestamp)}</span>
                  </div>
                ))}
              </div>
            </section>

            {/* Risk Distribution Chart */}
            <section className="panel chart-panel">
              <div className="panel-header"><h2><i className="fas fa-chart-pie"></i> Risk Distribution</h2></div>
              <div className="chart-container">
                <div className="donut-chart">
                  <svg viewBox="0 0 100 100">
                    <circle className="donut-ring" cx="50" cy="50" r="40" />
                    <DonutSegment type="safe" count={stats.safe} total={stats.total || 1} offset={0} />
                    <DonutSegment type="review" count={stats.review} total={stats.total || 1} offset={stats.safe} />
                    <DonutSegment type="suspicious" count={stats.suspicious} total={stats.total || 1} offset={stats.safe + stats.review} />
                  </svg>
                  <div className="donut-center">
                    <span className="donut-value">{stats.total ? Math.round((stats.safe / stats.total) * 100) : 0}%</span>
                    <span className="donut-label">Safe</span>
                  </div>
                </div>
                <div className="chart-legend">
                  <div className="legend-item"><span className="legend-dot safe"></span><span>Safe</span><span className="legend-value">{stats.safe}</span></div>
                  <div className="legend-item"><span className="legend-dot review"></span><span>Review</span><span className="legend-value">{stats.review}</span></div>
                  <div className="legend-item"><span className="legend-dot suspicious"></span><span>Suspicious</span><span className="legend-value">{stats.suspicious}</span></div>
                </div>
              </div>
            </section>

            {/* Quick Actions */}
            <section className="panel">
              <div className="panel-header"><h2><i className="fas fa-bolt"></i> Quick Actions</h2></div>
              <div className="quick-actions">
                <button className="action-btn" onClick={() => notify('success', 'Broadcast Sent', 'Message sent to all students')}>
                  <i className="fas fa-broadcast-tower"></i><span>Broadcast Message</span>
                </button>
                <button className="action-btn" onClick={() => notify('warning', 'Sessions Paused', 'All active sessions paused')}>
                  <i className="fas fa-pause-circle"></i><span>Pause All Sessions</span>
                </button>
                <button className="action-btn" onClick={() => notify('info', 'Snapshot Requested', 'Snapshots requested from all students')}>
                  <i className="fas fa-camera"></i><span>Request Snapshots</span>
                </button>
                <button className="action-btn" onClick={loadStudents}>
                  <i className="fas fa-sync-alt"></i><span>Refresh Data</span>
                </button>
                <button className="action-btn danger" onClick={() => notify('error', 'Emergency Lockdown', 'All sessions locked')}>
                  <i className="fas fa-lock"></i><span>Emergency Lockdown</span>
                </button>
              </div>
            </section>
          </aside>
        </div>
      </div>

      {selectedStudent && <StudentModal student={selectedStudent} onClose={() => setSelectedStudent(null)} />}
    </>
  );
}

function StatCard({ icon, color, value, label, trend, up, neutral }) {
  return (
    <div className="stat-card">
      <div className={`stat-icon ${color}`}><i className={`fas ${icon}`}></i></div>
      <div className="stat-info">
        <span className="stat-value">{value}</span>
        <span className="stat-label">{label}</span>
      </div>
      <div className={`stat-trend ${up ? 'up' : neutral ? 'neutral' : 'down'}`}>
        <i className={`fas fa-${up ? 'arrow-up' : neutral ? 'minus' : 'arrow-down'}`}></i>
        <span>{trend}</span>
      </div>
    </div>
  );
}

function DonutSegment({ type, count, total, offset }) {
  const circumference = 2 * Math.PI * 40;
  const pct = count / total;
  const offsetPct = offset / total;
  return (
    <circle
      className={`donut-segment ${type}`}
      cx="50" cy="50" r="40"
      style={{
        strokeDasharray: `${pct * circumference} ${circumference}`,
        strokeDashoffset: `${-offsetPct * circumference}`,
      }}
    />
  );
}
