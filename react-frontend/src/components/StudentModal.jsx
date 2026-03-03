import { getRiskStatus, getRiskClass } from '../utils';

export default function StudentModal({ student, onClose }) {
  if (!student) return null;

  return (
    <div className="modal active">
      <div className="modal-backdrop" onClick={onClose}></div>
      <div className="modal-content">
        <div className="modal-header">
          <h3>{student.name}</h3>
          <button className="modal-close" onClick={onClose}><i className="fas fa-times"></i></button>
        </div>
        <div className="modal-body">
          <div style={{ display: 'grid', gap: '1.5rem' }}>
            <div style={{ padding: '1rem', background: 'var(--bg-secondary)', borderRadius: 'var(--radius-md)' }}>
              <h4 style={{ marginBottom: '1rem', fontSize: '0.875rem', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <i className="fas fa-user" style={{ color: 'var(--accent-blue)' }}></i> Student Information
              </h4>
              <DetailRow label="Name" value={student.name} />
              <DetailRow label="Email" value={student.email} />
              <DetailRow label="Student ID" value={student.student_id || student.id} />
            </div>

            <div style={{ padding: '1rem', background: 'var(--bg-secondary)', borderRadius: 'var(--radius-md)' }}>
              <h4 style={{ marginBottom: '1rem', fontSize: '0.875rem', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <i className="fas fa-chart-line" style={{ color: 'var(--accent-blue)' }}></i> Risk Analysis
              </h4>
              <DetailRow label="Risk Score">
                <span className={getRiskClass(student.risk_score)} style={{ fontWeight: 700 }}>
                  {Math.round(student.risk_score)}%
                </span>
              </DetailRow>
              <DetailRow label="Status">
                <span className={`badge badge-${getRiskStatus(student.risk_score)}`}>
                  {getRiskStatus(student.risk_score).toUpperCase()}
                </span>
              </DetailRow>
              <DetailRow label="Engagement" value={`${Math.round(student.engagement_score || 0)}%`} />
              <DetailRow label="Effort Alignment" value={`${Math.round(student.effort_alignment || 0)}%`} />
            </div>
          </div>
        </div>
        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>Close</button>
          <button className="btn btn-primary">
            <i className="fas fa-file-pdf"></i> Generate Report
          </button>
        </div>
      </div>
    </div>
  );
}

function DetailRow({ label, value, children }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.5rem 0', borderBottom: '1px solid var(--border-color)' }}>
      <span style={{ color: 'var(--text-muted)' }}>{label}</span>
      {children || <span style={{ fontWeight: 500 }}>{value}</span>}
    </div>
  );
}
