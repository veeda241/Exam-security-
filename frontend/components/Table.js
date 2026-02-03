// Table Component - Student Analysis Table
export class StudentTable {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.data = [];
    }

    setData(data) {
        this.data = data;
        this.render();
    }

    render() {
        if (!this.container) return;

        if (this.data.length === 0) {
            this.container.innerHTML = '<tr><td colspan="6" class="loading">No students found</td></tr>';
            return;
        }

        this.container.innerHTML = this.data.map(student => this.renderRow(student)).join('');
    }

    renderRow(student) {
        const badgeClass = this.getBadgeClass(student.status);
        const riskColor = this.getRiskColor(student.risk_score);

        return `
      <tr data-student-id="${student.student_id}">
        <td>
          <div style="font-weight: 500;">${student.name}</div>
          <div style="font-size: 0.75rem; color: var(--text-secondary);">${student.email}</div>
        </td>
        <td>
          <span class="badge ${badgeClass}">${(student.status || 'unknown').toUpperCase()}</span>
        </td>
        <td>
          <span style="font-weight: 600; color: ${riskColor}">${Math.round(student.risk_score)}</span>
        </td>
        <td>
          <div class="score-bar">
            <div class="score-fill" style="width: ${student.engagement_score}%"></div>
          </div>
          <span style="font-size: 0.75rem;">${Math.round(student.engagement_score)}%</span>
        </td>
        <td>
          <div class="score-bar">
            <div class="score-fill" style="width: ${student.effort_alignment}%; background-color: #8b5cf6;"></div>
          </div>
          <span style="font-size: 0.75rem;">${Math.round(student.effort_alignment)}%</span>
        </td>
        <td>
          <button class="btn-details" onclick="viewDetails('${student.student_id}')">Details</button>
        </td>
      </tr>
    `;
    }

    getBadgeClass(status) {
        switch (status) {
            case 'safe': return 'badge-safe';
            case 'review': return 'badge-review';
            case 'suspicious': return 'badge-suspicious';
            default: return 'badge-safe';
        }
    }

    getRiskColor(score) {
        if (score > 60) return '#ef4444';
        if (score > 30) return '#f59e0b';
        return '#10b981';
    }

    filter(searchTerm, statusFilter) {
        const filtered = this.data.filter(student => {
            const matchesSearch = student.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                student.email.toLowerCase().includes(searchTerm.toLowerCase());
            const matchesStatus = statusFilter === 'all' || student.status === statusFilter;
            return matchesSearch && matchesStatus;
        });

        this.container.innerHTML = filtered.map(s => this.renderRow(s)).join('');
    }
}
