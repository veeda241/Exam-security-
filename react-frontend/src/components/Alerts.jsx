import { useMemo } from 'react';
import { useApp } from '../context/AppContext';
import { formatTime } from '../utils';
import Header from '../components/Header';

export default function Alerts() {
  const { state, dispatch } = useApp();

  const alerts = useMemo(() =>
    state.activities.filter(a => a.type === 'danger' || a.type === 'warning'),
    [state.activities]
  );

  const stats = useMemo(() => ({
    total: alerts.length,
    critical: alerts.filter(a => a.type === 'danger').length,
    face: alerts.filter(a => a.title?.includes('Face')).length,
    tab: alerts.filter(a => a.title?.includes('Tab')).length,
  }), [alerts]);

  return (
    <>
      <Header title="Alert Log" />
      <div className="dashboard-content">
        <section className="stats-row">
          <div className="stat-card"><div className="stat-icon red"><i className="fas fa-bell"></i></div><div className="stat-info"><span className="stat-value">{stats.total}</span><span className="stat-label">Total Alerts</span></div></div>
          <div className="stat-card"><div className="stat-icon yellow"><i className="fas fa-exclamation-circle"></i></div><div className="stat-info"><span className="stat-value">{stats.critical}</span><span className="stat-label">Critical</span></div></div>
          <div className="stat-card"><div className="stat-icon blue"><i className="fas fa-eye-slash"></i></div><div className="stat-info"><span className="stat-value">{stats.face}</span><span className="stat-label">Face Absence</span></div></div>
          <div className="stat-card"><div className="stat-icon purple"><i className="fas fa-window-restore"></i></div><div className="stat-info"><span className="stat-value">{stats.tab}</span><span className="stat-label">Tab Switches</span></div></div>
        </section>

        <div className="main-grid">
          <section className="panel" style={{ minHeight: 500 }}>
            <div className="panel-header">
              <h2><i className="fas fa-bell"></i> Alert Log</h2>
              <div className="panel-actions">
                <button className="btn btn-secondary" onClick={() => dispatch({ type: 'ADD_TOAST', payload: { type: 'success', title: 'Alerts Cleared', message: 'All alerts marked as read' } })}>
                  <i className="fas fa-check-double"></i> Mark All Read
                </button>
              </div>
            </div>
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr><th>Time</th><th>Severity</th><th>Type</th><th>Student</th><th>Description</th><th>Actions</th></tr>
                </thead>
                <tbody>
                  {alerts.length === 0 ? (
                    <tr className="loading-row"><td colSpan="6"><div className="loading-spinner"><i className="fas fa-inbox"></i><span>No alerts recorded</span></div></td></tr>
                  ) : alerts.map((alert, i) => {
                    const severity = alert.type === 'danger' ? 'suspicious' : 'review';
                    return (
                      <tr key={i}>
                        <td style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>{formatTime(alert.timestamp)}</td>
                        <td><span className={`badge badge-${severity}`}>{alert.type === 'danger' ? 'CRITICAL' : 'WARNING'}</span></td>
                        <td>{alert.title}</td>
                        <td>{alert.description}</td>
                        <td style={{ fontSize: '0.85rem' }}>{alert.title}</td>
                        <td><button className="btn-details" onClick={() => dispatch({ type: 'ADD_TOAST', payload: { type: 'info', title: 'Alert Dismissed', message: 'Alert has been dismissed' } })}>
                          <i className="fas fa-check"></i> Dismiss
                        </button></td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <div className="panel-footer"><span className="results-count">Showing {alerts.length} alerts</span></div>
          </section>

          <aside className="side-panels">
            <section className="panel">
              <div className="panel-header"><h2><i className="fas fa-chart-bar"></i> Alert Breakdown</h2></div>
              <div style={{ padding: '1rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                <BreakdownRow icon="fa-user-slash" color="var(--accent-red)" label="Face Missing" count={stats.face} badge="suspicious" />
                <BreakdownRow icon="fa-window-restore" color="var(--accent-blue)" label="Tab Switches" count={stats.tab} badge="review" />
                <BreakdownRow icon="fa-clipboard" color="var(--accent-purple)" label="Copy/Paste" count={0} badge="review" />
              </div>
            </section>

            <section className="panel">
              <div className="panel-header"><h2><i className="fas fa-bolt"></i> Quick Response</h2></div>
              <div className="quick-actions">
                <button className="action-btn" onClick={() => dispatch({ type: 'ADD_TOAST', payload: { type: 'success', title: 'Broadcast Sent', message: 'Warning sent to all students' } })}>
                  <i className="fas fa-broadcast-tower"></i><span>Broadcast Warning</span>
                </button>
                <button className="action-btn danger" onClick={() => dispatch({ type: 'ADD_TOAST', payload: { type: 'error', title: 'Emergency Lockdown', message: 'All sessions locked' } })}>
                  <i className="fas fa-lock"></i><span>Emergency Lockdown</span>
                </button>
              </div>
            </section>
          </aside>
        </div>
      </div>
    </>
  );
}

function BreakdownRow({ icon, color, label, count, badge }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.75rem 1rem', background: 'var(--bg-secondary)', borderRadius: 'var(--radius-md)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
        <i className={`fas ${icon}`} style={{ color }}></i><span>{label}</span>
      </div>
      <span className={`badge badge-${badge}`}>{count}</span>
    </div>
  );
}
