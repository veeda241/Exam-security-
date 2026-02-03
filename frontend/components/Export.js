// Export Component - CSV/PDF Export
export class ExportHandler {
    constructor() {
        this.data = [];
    }

    setData(data) {
        this.data = data;
    }

    exportCSV(filename = 'examguard_report.csv') {
        if (this.data.length === 0) {
            alert('No data to export');
            return;
        }

        const headers = ['Name', 'Email', 'Status', 'Risk Score', 'Engagement', 'Effort Alignment'];
        const rows = this.data.map(student => [
            student.name,
            student.email,
            student.status,
            student.risk_score,
            student.engagement_score,
            student.effort_alignment
        ]);

        const csvContent = [
            headers.join(','),
            ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
        ].join('\n');

        this.downloadFile(csvContent, filename, 'text/csv');
    }

    async exportPDF(filename = 'examguard_report.pdf') {
        // For PDF export, we'd typically use a library like jsPDF
        // This is a placeholder that generates a basic HTML-based print
        const printWindow = window.open('', '_blank');

        const html = `
      <!DOCTYPE html>
      <html>
      <head>
        <title>ExamGuard Pro Report</title>
        <style>
          body { font-family: Arial, sans-serif; padding: 20px; }
          h1 { color: #3b82f6; }
          table { width: 100%; border-collapse: collapse; margin-top: 20px; }
          th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
          th { background-color: #f3f4f6; }
          .risk-high { color: #ef4444; }
          .risk-medium { color: #f59e0b; }
          .risk-low { color: #10b981; }
        </style>
      </head>
      <body>
        <h1>🛡️ ExamGuard Pro - Analysis Report</h1>
        <p>Generated: ${new Date().toLocaleString()}</p>
        <table>
          <thead>
            <tr>
              <th>Student</th>
              <th>Email</th>
              <th>Status</th>
              <th>Risk Score</th>
              <th>Engagement</th>
              <th>Effort</th>
            </tr>
          </thead>
          <tbody>
            ${this.data.map(s => `
              <tr>
                <td>${s.name}</td>
                <td>${s.email}</td>
                <td>${s.status}</td>
                <td class="${this.getRiskClass(s.risk_score)}">${Math.round(s.risk_score)}</td>
                <td>${Math.round(s.engagement_score)}%</td>
                <td>${Math.round(s.effort_alignment)}%</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </body>
      </html>
    `;

        printWindow.document.write(html);
        printWindow.document.close();
        printWindow.print();
    }

    getRiskClass(score) {
        if (score > 60) return 'risk-high';
        if (score > 30) return 'risk-medium';
        return 'risk-low';
    }

    downloadFile(content, filename, mimeType) {
        const blob = new Blob([content], { type: mimeType });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    }
}
