export function getRiskStatus(score) {
  if (score > 60) return 'suspicious';
  if (score > 30) return 'review';
  return 'safe';
}

export function getRiskClass(score) {
  if (score > 60) return 'risk-high';
  if (score > 30) return 'risk-medium';
  return 'risk-low';
}

export function getInitials(name) {
  return (name || 'U')
    .split(' ')
    .map(n => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
}

export function formatTime(date) {
  const now = new Date();
  const diff = (now - new Date(date)) / 1000;
  if (diff < 60) return 'Just now';
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return new Date(date).toLocaleDateString();
}

export function exportCSV(students) {
  const headers = ['Name', 'Email', 'Status', 'Risk Score', 'Engagement', 'Effort'];
  const rows = students.map(s => [
    s.name,
    s.email,
    getRiskStatus(s.risk_score),
    Math.round(s.risk_score),
    Math.round(s.engagement_score || 0),
    Math.round(s.effort_alignment || 0),
  ]);

  const csv = [headers.join(','), ...rows.map(r => r.map(c => `"${c}"`).join(','))].join('\n');
  const blob = new Blob([csv], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `examguard-report-${new Date().toISOString().split('T')[0]}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}
