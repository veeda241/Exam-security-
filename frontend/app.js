// Frontend App - Main JavaScript
import { StudentTable } from './components/Table.js';
import { FilterControls } from './components/Filters.js';
import { ExportHandler } from './components/Export.js';

const API_BASE = '/api/analysis';

// State
let studentsData = [];
let studentTable;
let filterControls;
let exportHandler;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Initialize components
    studentTable = new StudentTable('studentTableBody');

    filterControls = new FilterControls((filters) => {
        studentTable.filter(filters.search, filters.status);
    });
    filterControls.init();

    exportHandler = new ExportHandler();

    // Start clock
    updateTime();
    setInterval(updateTime, 1000);

    // Fetch initial data
    fetchData();

    // Auto refresh every 10 seconds
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
        studentTable.setData(studentsData);
        exportHandler.setData(studentsData);
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

// Global functions for inline event handlers
window.filterTable = function () {
    const searchTerm = document.getElementById('searchInput').value;
    const statusFilter = document.getElementById('statusFilter').value;
    studentTable.filter(searchTerm, statusFilter);
};

window.viewDetails = function (studentId) {
    // Navigate to details or open modal
    window.location.href = `/student/${studentId}`;
};

window.exportData = function () {
    exportHandler.exportCSV();
};

window.fetchData = fetchData;
