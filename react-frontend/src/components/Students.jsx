import { useState, useMemo } from 'react';
import { useApp } from '../context/AppContext';
import { getRiskStatus, getRiskClass, getInitials, exportCSV } from '../utils';
import Header from '../components/Header';
import StudentModal from '../components/StudentModal';

export default function Students() {
  const { state, dispatch } = useApp();
  const [search, setSearch] = useState('');
  const [riskFilter, setRiskFilter] = useState('all');
  const [selectedStudent, setSelectedStudent] = useState(null);

  const students = useMemo(() => {
    return state.students.filter(s => {
      if (search) {
        const q = search.toLowerCase();
        if (!s.name?.toLowerCase().includes(q) && !s.email?.toLowerCase().includes(q)) return false;
      }
      if (riskFilter !== 'all' && getRiskStatus(s.risk_score) !== riskFilter) return false;
      return true;
    });
  }, [state.students, search, riskFilter]);

  const stats = useMemo(() => ({
    total: state.students.length,
    online: state.students.length,
    flagged: state.students.filter(s => (s.risk_score || 0) > 60).length,
    avgRisk: state.students.length
      ? Math.round(state.students.reduce((a, s) => a + (s.risk_score || 0), 0) / state.students.length) : 0,
  }), [state.students]);

  return (
    <>
      <Header title="Student Directory" />
      <div className="dashboard-content">
        <section className="stats-row">
          <div className="stat-card"><div className="stat-icon blue"><i className="fas fa-users"></i></div><div className="stat-info"><span className="stat-value">{stats.total}</span><span className="stat-label">Total Students</span></div></div>
          <div className="stat-card"><div className="stat-icon green"><i className="fas fa-user-check"></i></div><div className="stat-info"><span className="stat-value">{stats.online}</span><span className="stat-label">Online Now</span></div></div>
          <div className="stat-card"><div className="stat-icon red"><i className="fas fa-user-shield"></i></div><div className="stat-info"><span className="stat-value">{stats.flagged}</span><span className="stat-label">Flagged</span></div></div>
          <div className="stat-card"><div className="stat-icon purple"><i className="fas fa-graduation-cap"></i></div><div className="stat-info"><span className="stat-value">{stats.avgRisk}</span><span className="stat-label">Avg Risk Score</span></div></div>
        </section>

        <section className="panel" style={{ flex: 1 }}>
          <div className="panel-header">
            <h2><i className="fas fa-user-graduate"></i> Student Directory</h2>
            <div className="panel-actions">
              <div className="search-box" style={{ maxWidth: 260 }}>
                <i className="fas fa-search"></i>
                <input type="text" placeholder="Search students..." value={search} onChange={e => setSearch(e.target.value)} />
              </div>
              <select className="filter-select" value={riskFilter} onChange={e => setRiskFilter(e.target.value)}>
                <option value="all">All Risk Levels</option>
                <option value="safe">Safe</option>
                <option value="review">Review</option>
                <option value="suspicious">Suspicious</option>
              </select>
              <button className="btn btn-primary" onClick={() => { exportCSV(students); dispatch({ type: 'ADD_TOAST', payload: { type: 'success', title: 'Export Complete', message: `Exported ${students.length} students` } }); }}>
                <i className="fas fa-download"></i> Export CSV
              </button>
            </div>
          </div>
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr><th>Student</th><th>Email</th><th>Status</th><th>Risk Score</th><th>Engagement</th><th title="Tab Switches"><i className="fas fa-window-restore"></i></th><th title="Flagged Sites"><i className="fas fa-ban"></i></th><th title="Copy/Paste"><i className="fas fa-copy"></i></th><th>Actions</th></tr>
              </thead>
              <tbody>
                {students.length === 0 ? (
                  <tr className="loading-row"><td colSpan="9"><div className="loading-spinner"><i className="fas fa-inbox"></i><span>No students found</span></div></td></tr>
                ) : students.map(s => {
                  const status = getRiskStatus(s.risk_score);
                  const tabSwitches = s.tab_switch_count || 0;
                  const flaggedSites = s.forbidden_site_count || 0;
                  const copyCount = s.copy_count || 0;
                  return (
                    <tr key={s.student_id || s.id} className={status === 'suspicious' ? 'row-suspicious' : ''}>
                      <td>
                        <div className="student-cell">
                          <div className={`student-avatar avatar-${status}`}>{getInitials(s.name)}</div>
                          <span className="student-name">{s.name}</span>
                        </div>
                      </td>
                      <td style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>{s.email}</td>
                      <td><span className={`badge badge-${status}`}>{status.toUpperCase()}</span></td>
                      <td><span className={getRiskClass(s.risk_score)} style={{ fontWeight: 600 }}>{Math.round(s.risk_score)}%</span></td>
                      <td>{Math.round(s.engagement_score || 0)}%</td>
                      <td><span className={`action-count ${tabSwitches > 5 ? 'warn' : tabSwitches > 10 ? 'danger' : ''}`}>{tabSwitches}</span></td>
                      <td><span className={`action-count ${flaggedSites > 0 ? 'danger' : ''}`}>{flaggedSites}</span></td>
                      <td><span className={`action-count ${copyCount > 3 ? 'warn' : ''}`}>{copyCount}</span></td>
                      <td>
                        <button className="btn-details" style={{ marginRight: 4 }} onClick={() => setSelectedStudent(s)}>
                          <i className="fas fa-eye"></i> View
                        </button>
                        <button className="btn-details" style={{ backgroundColor: 'var(--bg-secondary)', color: 'var(--accent-yellow)', borderColor: 'var(--accent-yellow)' }}
                          onClick={() => dispatch({ type: 'ADD_TOAST', payload: { type: 'warning', title: 'Warning Sent', message: `Warning sent to ${s.name}` } })}>
                          <i className="fas fa-exclamation-triangle"></i> Warn
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <div className="panel-footer"><span className="results-count">Showing {students.length} students</span></div>
        </section>
      </div>
      {selectedStudent && <StudentModal student={selectedStudent} onClose={() => setSelectedStudent(null)} />}
    </>
  );
}
