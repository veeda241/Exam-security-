import { useApp } from '../context/AppContext';
import Header from '../components/Header';

export default function Reports() {
  const { dispatch } = useApp();

  return (
    <>
      <Header title="Reports" />
      <div className="dashboard-content">
        <section className="stats-row">
          <div className="stat-card"><div className="stat-icon blue"><i className="fas fa-file-alt"></i></div><div className="stat-info"><span className="stat-value">0</span><span className="stat-label">Reports Generated</span></div></div>
          <div className="stat-card"><div className="stat-icon green"><i className="fas fa-file-download"></i></div><div className="stat-info"><span className="stat-value">0</span><span className="stat-label">Downloaded</span></div></div>
          <div className="stat-card"><div className="stat-icon yellow"><i className="fas fa-clock"></i></div><div className="stat-info"><span className="stat-value">0</span><span className="stat-label">Pending Review</span></div></div>
          <div className="stat-card"><div className="stat-icon red"><i className="fas fa-flag"></i></div><div className="stat-info"><span className="stat-value">0</span><span className="stat-label">Flagged Sessions</span></div></div>
        </section>

        <div className="main-grid">
          <section className="panel" style={{ minHeight: 500 }}>
            <div className="panel-header">
              <h2><i className="fas fa-file-alt"></i> Session Reports</h2>
              <div className="panel-actions">
                <button className="btn btn-primary" onClick={() => dispatch({ type: 'ADD_TOAST', payload: { type: 'info', title: 'Generating Report', message: 'Batch report is being generated...' } })}>
                  <i className="fas fa-file-pdf"></i> Generate Batch Report
                </button>
              </div>
            </div>
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr><th>Report ID</th><th>Type</th><th>Session / Student</th><th>Generated</th><th>Status</th><th>Risk Summary</th><th>Actions</th></tr>
                </thead>
                <tbody>
                  <tr className="loading-row"><td colSpan="7"><div className="loading-spinner"><i className="fas fa-inbox"></i><span>No reports generated yet</span></div></td></tr>
                </tbody>
              </table>
            </div>
            <div className="panel-footer"><span className="results-count">Showing 0 reports</span></div>
          </section>

          <aside className="side-panels">
            <section className="panel">
              <div className="panel-header"><h2><i className="fas fa-cogs"></i> Report Generator</h2></div>
              <div style={{ padding: '1rem' }}>
                <div style={{ marginBottom: '1rem' }}>
                  <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'block', marginBottom: '0.5rem' }}>Report Type</label>
                  <select className="filter-select" style={{ width: '100%' }}>
                    <option>Session Summary</option>
                    <option>Student Profile</option>
                    <option>Incident Report</option>
                    <option>Full Audit Trail</option>
                  </select>
                </div>
                <div style={{ marginBottom: '1rem' }}>
                  <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'block', marginBottom: '0.5rem' }}>Format</label>
                  <select className="filter-select" style={{ width: '100%' }}>
                    <option>PDF</option>
                    <option>JSON</option>
                    <option>CSV</option>
                  </select>
                </div>
                <button className="btn btn-primary" style={{ width: '100%', justifyContent: 'center' }}
                  onClick={() => dispatch({ type: 'ADD_TOAST', payload: { type: 'info', title: 'Generating Report', message: 'Report is being generated...' } })}>
                  <i className="fas fa-magic"></i> Generate Report
                </button>
              </div>
            </section>

            <section className="panel">
              <div className="panel-header"><h2><i className="fas fa-history"></i> Recent Downloads</h2></div>
              <div className="activity-feed" style={{ padding: '0.5rem', minHeight: 120 }}>
                <div className="empty-state"><i className="fas fa-download"></i><p>No recent downloads</p></div>
              </div>
            </section>
          </aside>
        </div>
      </div>
    </>
  );
}
