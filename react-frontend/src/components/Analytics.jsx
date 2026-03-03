import Header from '../components/Header';

export default function Analytics() {
  return (
    <>
      <Header title="Analytics" />
      <div className="dashboard-content">
        <section className="stats-row">
          <div className="stat-card"><div className="stat-icon cyan"><i className="fas fa-brain"></i></div><div className="stat-info"><span className="stat-value">0</span><span className="stat-label">AI Scans Today</span></div></div>
          <div className="stat-card"><div className="stat-icon green"><i className="fas fa-shield-alt"></i></div><div className="stat-info"><span className="stat-value">100%</span><span className="stat-label">Exam Integrity</span></div></div>
          <div className="stat-card"><div className="stat-icon yellow"><i className="fas fa-tachometer-alt"></i></div><div className="stat-info"><span className="stat-value">0</span><span className="stat-label">Avg Risk Score</span></div></div>
          <div className="stat-card"><div className="stat-icon purple"><i className="fas fa-robot"></i></div><div className="stat-info"><span className="stat-value">97%</span><span className="stat-label">ML Accuracy</span></div></div>
        </section>

        <div className="main-grid">
          <section className="panel" style={{ minHeight: 500 }}>
            <div className="panel-header">
              <h2><i className="fas fa-chart-line"></i> Analytics Overview</h2>
              <div className="panel-actions">
                <select className="filter-select">
                  <option value="today">Today</option>
                  <option value="week">This Week</option>
                  <option value="month">This Month</option>
                  <option value="all">All Time</option>
                </select>
              </div>
            </div>
            <div style={{ padding: '1.5rem', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
              {/* Risk Trend */}
              <div style={{ background: 'var(--bg-secondary)', borderRadius: 'var(--radius-md)', padding: '1.25rem' }}>
                <h4 style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
                  <i className="fas fa-chart-area" style={{ color: 'var(--accent-blue)', marginRight: '0.5rem' }}></i>Risk Score Trend
                </h4>
                <div style={{ display: 'flex', alignItems: 'flex-end', gap: 6, height: 120 }}>
                  {[20,25,30,45,40,35,28,22,50,65,45,30].map((h, i) => (
                    <div key={i} style={{
                      flex: 1,
                      background: h > 60 ? 'var(--accent-red)' : h > 30 ? 'var(--accent-yellow)' : 'var(--accent-green)',
                      borderRadius: '4px 4px 0 0',
                      height: `${h}%`,
                      opacity: 0.8,
                    }}></div>
                  ))}
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '0.5rem', fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                  <span>6h ago</span><span>Now</span>
                </div>
              </div>

              {/* Event Distribution */}
              <div style={{ background: 'var(--bg-secondary)', borderRadius: 'var(--radius-md)', padding: '1.25rem' }}>
                <h4 style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
                  <i className="fas fa-chart-pie" style={{ color: 'var(--accent-purple)', marginRight: '0.5rem' }}></i>Event Distribution
                </h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                  <DistributionBar label="Tab Switches" pct={42} color="blue" />
                  <DistributionBar label="Face Absence" pct={28} color="red" />
                  <DistributionBar label="Copy/Paste" pct={18} color="yellow" />
                  <DistributionBar label="Other" pct={12} color="purple" />
                </div>
              </div>

              {/* System Performance */}
              <div style={{ background: 'var(--bg-secondary)', borderRadius: 'var(--radius-md)', padding: '1.25rem' }}>
                <h4 style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
                  <i className="fas fa-server" style={{ color: 'var(--accent-cyan)', marginRight: '0.5rem' }}></i>System Performance
                </h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                  <PerfRow label="API Response" value="45ms" color="var(--accent-green)" />
                  <PerfRow label="WebSocket Latency" value="12ms" color="var(--accent-green)" />
                  <PerfRow label="Face Detection" value="120ms" color="var(--accent-yellow)" />
                  <PerfRow label="OCR Processing" value="350ms" color="var(--accent-yellow)" />
                  <PerfRow label="DB Queries" value="8ms" color="var(--accent-green)" />
                </div>
              </div>

              {/* Engagement Heatmap */}
              <div style={{ background: 'var(--bg-secondary)', borderRadius: 'var(--radius-md)', padding: '1.25rem' }}>
                <h4 style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
                  <i className="fas fa-fire" style={{ color: 'var(--accent-yellow)', marginRight: '0.5rem' }}></i>Engagement Heatmap
                </h4>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(8,1fr)', gap: 4 }}>
                  {[0.7,0.5,0.8,0.5,0.6,0.9,0.3,0.4,0.6,0.7,0.4,0.8,0.5,0.3,0.9,0.6].map((v, i) => (
                    <div key={i} style={{
                      aspectRatio: '1',
                      background: v < 0.4 ? `rgba(239,68,68,${v+0.2})` : v < 0.6 ? `rgba(245,158,11,${v})` : `rgba(16,185,129,${v})`,
                      borderRadius: 4,
                    }}></div>
                  ))}
                </div>
              </div>
            </div>
          </section>

          <aside className="side-panels">
            <section className="panel">
              <div className="panel-header"><h2><i className="fas fa-robot"></i> AI Modules</h2></div>
              <div style={{ padding: '1rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {['Face Detection', 'OCR Engine', 'Transformer NLP', 'Anomaly Detection', 'Plagiarism Check'].map(m => (
                  <div key={m} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.75rem 1rem', background: 'var(--bg-secondary)', borderRadius: 'var(--radius-md)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                      <i className="fas fa-check-circle" style={{ color: 'var(--accent-green)' }}></i>
                      <span style={{ fontSize: '0.875rem' }}>{m}</span>
                    </div>
                    <span className="badge badge-safe">Active</span>
                  </div>
                ))}
              </div>
            </section>

            <section className="panel">
              <div className="panel-header"><h2><i className="fas fa-plug"></i> Connections</h2></div>
              <div style={{ padding: '1rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                <PerfRow label="WebSocket Clients" value="0" color="var(--accent-blue)" />
                <PerfRow label="Active Proctors" value="0" color="var(--accent-green)" />
                <PerfRow label="Student Extensions" value="0" color="var(--accent-purple)" />
                <PerfRow label="Events/min" value="0" color="var(--accent-yellow)" />
              </div>
            </section>
          </aside>
        </div>
      </div>
    </>
  );
}

function DistributionBar({ label, pct, color }) {
  const colors = { blue: 'var(--accent-blue)', red: 'var(--accent-red)', yellow: 'var(--accent-yellow)', purple: 'var(--accent-purple)' };
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: 4 }}>
        <span>{label}</span><span style={{ color: colors[color] }}>{pct}%</span>
      </div>
      <div className="progress-bar" style={{ width: '100%' }}>
        <div className="progress-fill" style={{ width: `${pct}%`, background: colors[color] }}></div>
      </div>
    </div>
  );
}

function PerfRow({ label, value, color }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
      <span>{label}</span><span style={{ color, fontWeight: 600 }}>{value}</span>
    </div>
  );
}
