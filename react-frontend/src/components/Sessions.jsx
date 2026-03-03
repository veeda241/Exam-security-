import { useMemo } from 'react';
import { useApp } from '../context/AppContext';
import { getRiskStatus, getRiskClass } from '../utils';
import Header from '../components/Header';

export default function Sessions() {
  const { state, dispatch } = useApp();

  const sessionStats = useMemo(() => {
    const active = state.sessions.filter(s => s.status === 'active').length;
    const completed = state.sessions.filter(s => s.status === 'completed').length;
    return { active, completed, total: state.sessions.length, participants: state.students.length };
  }, [state.sessions, state.students]);

  function notify(type, title, message) {
    dispatch({ type: 'ADD_TOAST', payload: { type, title, message } });
  }

  return (
    <>
      <Header title="Active Sessions" />
      <div className="dashboard-content">
        <section className="stats-row">
          <div className="stat-card">
            <div className="stat-icon blue"><i className="fas fa-desktop"></i></div>
            <div className="stat-info"><span className="stat-value">{sessionStats.active}</span><span className="stat-label">Active Sessions</span></div>
          </div>
          <div className="stat-card">
            <div className="stat-icon green"><i className="fas fa-check-circle"></i></div>
            <div className="stat-info"><span className="stat-value">{sessionStats.completed}</span><span className="stat-label">Completed</span></div>
          </div>
          <div className="stat-card">
            <div className="stat-icon yellow"><i className="fas fa-clock"></i></div>
            <div className="stat-info"><span className="stat-value">--</span><span className="stat-label">Avg Duration</span></div>
          </div>
          <div className="stat-card">
            <div className="stat-icon purple"><i className="fas fa-user-friends"></i></div>
            <div className="stat-info"><span className="stat-value">{sessionStats.participants}</span><span className="stat-label">Total Participants</span></div>
          </div>
        </section>

        <section className="panel" style={{ flex: 1 }}>
          <div className="panel-header">
            <h2><i className="fas fa-desktop"></i> Exam Sessions</h2>
            <div className="panel-actions">
              <button className="btn btn-primary" onClick={() => notify('success', 'Session Created', 'New session created')}>
                <i className="fas fa-plus"></i> New Session
              </button>
            </div>
          </div>
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Session ID</th>
                  <th>Exam Name</th>
                  <th>Status</th>
                  <th>Students</th>
                  <th>Started</th>
                  <th>Avg Risk</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {state.sessions.length === 0 ? (
                  <tr className="loading-row">
                    <td colSpan="7"><div className="loading-spinner"><i className="fas fa-inbox"></i><span>No active sessions</span></div></td>
                  </tr>
                ) : state.sessions.map(session => {
                  const sessionStudents = state.students.filter(s => s.session_id === session.id);
                  const avgRisk = sessionStudents.length
                    ? Math.round(sessionStudents.reduce((a, s) => a + (s.risk_score || 0), 0) / sessionStudents.length) : 0;
                  const started = session.start_time ? new Date(session.start_time).toLocaleTimeString() : '--';
                  const statusClass = session.status === 'active' ? 'safe' : session.status === 'paused' ? 'review' : 'suspicious';

                  return (
                    <tr key={session.id}>
                      <td><code style={{ color: 'var(--accent-blue)', fontSize: '0.8rem' }}>{(session.id || '').slice(0, 8)}...</code></td>
                      <td>{session.name || session.exam_name || 'Exam Session'}</td>
                      <td><span className={`badge badge-${statusClass}`}>{(session.status || 'active').toUpperCase()}</span></td>
                      <td>{sessionStudents.length}</td>
                      <td>{started}</td>
                      <td><span className={getRiskClass(avgRisk)}>{avgRisk}%</span></td>
                      <td>
                        <button className="btn-details" onClick={() => notify('info', 'Session Details', `Viewing session ${(session.id || '').slice(0, 8)}`)}>
                          <i className="fas fa-eye"></i> View
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <div className="panel-footer"><span className="results-count">Showing {state.sessions.length} sessions</span></div>
        </section>
      </div>
    </>
  );
}
