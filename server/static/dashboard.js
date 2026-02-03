// Dashboard Logic
const API_BASE = '/api/analysis';

let studentsData = [];

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    updateTime();
    setInterval(updateTime, 1000);
    fetchData();
    // Auto refresh every 10s
    setInterval(fetchData, 10000);
});

function updateTime() {
    const now = new Date();
    document.getElementById('currentTime').textContent = now.toLocaleTimeString();
}

async function fetchData() {
    try {
        const response = await fetch(`${API_BASE}/dashboard`);
        if (!response.ok) throw new Error('Failed to fetch data');

        studentsData = await response.json();
        renderTable(studentsData);
        updateMetrics(studentsData);
    } catch (error) {
        console.error('Error fetching data:', error);
    }
}

function updateMetrics(data) {
    document.getElementById('totalStudents').textContent = data.length;

    const highRisk = data.filter(s => s.status === 'suspicious').length;
    document.getElementById('highRiskCount').textContent = highRisk;

    const totalEngagement = data.reduce((acc, s) => acc + (s.engagement_score || 0), 0);
    const avgEngagement = data.length ? Math.round(totalEngagement / data.length) : 0;
    document.getElementById('avgEngagement').textContent = `${avgEngagement}%`;

    const totalEffort = data.reduce((acc, s) => acc + (s.effort_alignment || 0), 0);
    const avgEffort = data.length ? Math.round(totalEffort / data.length) : 0;
    document.getElementById('avgEffort').textContent = `${avgEffort}%`;
}

function renderTable(data) {
    const tbody = document.getElementById('studentTableBody');
    tbody.innerHTML = '';

    if (data.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="loading">No active students found</td></tr>';
        return;
    }

    data.forEach(student => {
        const tr = document.createElement('tr');

        // Status Badge
        let badgeClass = 'badge-safe';
        if (student.status === 'review') badgeClass = 'badge-review';
        if (student.status === 'suspicious') badgeClass = 'badge-suspicious';

        // Risk Color
        let riskColor = '#10b981';
        if (student.risk_score > 30) riskColor = '#f59e0b';
        if (student.risk_score > 60) riskColor = '#ef4444';

        tr.innerHTML = `
            <td>
                <div style="font-weight: 500;">${student.name}</div>
                <div style="font-size: 0.75rem; color: var(--text-secondary);">${student.email}</div>
            </td>
            <td><span class="badge ${badgeClass}">${student.status ? student.status.toUpperCase() : 'UNKNOWN'}</span></td>
            <td>
                <div style="display: flex; align-items: center; gap: 0.5rem;">
                    <span style="font-weight: 600; color: ${riskColor}">${Math.round(student.risk_score)}</span>
                </div>
            </td>
            <td>
                <div class="score-bar"><div class="score-fill" style="width: ${student.engagement_score}%"></div></div>
                <span style="font-size: 0.75rem;">${Math.round(student.engagement_score)}%</span>
            </td>
            <td>
                <div class="score-bar"><div class="score-fill" style="width: ${student.effort_alignment}%; background-color: #8b5cf6;"></div></div>
                <span style="font-size: 0.75rem;">${Math.round(student.effort_alignment)}%</span>
            </td>
            <td>
                <button style="font-size: 0.75rem; padding: 0.25rem 0.5rem;" onclick="viewDetails('${student.student_id}')">Details</button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function filterTable() {
    const searchTerm = document.getElementById('searchInput').value.toLowerCase();
    const statusFilter = document.getElementById('statusFilter').value;

    const filtered = studentsData.filter(student => {
        const matchesSearch = student.name.toLowerCase().includes(searchTerm) ||
            student.email.toLowerCase().includes(searchTerm);
        const matchesStatus = statusFilter === 'all' || student.status === statusFilter;

        return matchesSearch && matchesStatus;
    });

    renderTable(filtered);
}

function viewDetails(studentId) {
    // Navigate to details page (can be implemented later or modal)
    alert('Detail view for ' + studentId + ' coming soon');
}

function exportData() {
    const csvContent = "data:text/csv;charset=utf-8,"
        + "Name,Email,Status,Risk Score,Engagement,Effort Alignment\n"
        + studentsData.map(e => `${e.name},${e.email},${e.status},${e.risk_score},${e.engagement_score},${e.effort_alignment}`).join("\n");

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", "examguard_report.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}
