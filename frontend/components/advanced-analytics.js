/**
 * ExamGuard Pro - Advanced Analytics Dashboard Component
 * Visualizations for: Biometrics, Gaze Tracking, Forensics, Audio Analysis
 * 
 * This component adds real-time visualization panels to the dashboard.
 */

class AdvancedAnalyticsDashboard {
    constructor(options = {}) {
        this.apiBase = options.apiBase || '/api/analytics';
        this.refreshInterval = options.refreshInterval || 5000;
        this.selectedStudent = null;
        
        // Canvas contexts for visualizations
        this.gazeHeatmapCanvas = null;
        this.biometricsCanvas = null;
        
        this.intervalId = null;
    }
    
    // =========================================================================
    // Initialization
    // =========================================================================
    
    init() {
        this.createPanels();
        this.bindEvents();
        this.startAutoRefresh();
        
        console.log('[AdvancedAnalytics] Dashboard initialized');
    }
    
    createPanels() {
        // Find the dashboard container (adjust selector as needed)
        const dashboard = document.querySelector('.dashboard-grid') || 
                         document.querySelector('.content') ||
                         document.body;
        
        // Create the advanced analytics section
        const section = document.createElement('section');
        section.className = 'advanced-analytics-section';
        section.innerHTML = this.getPanelHTML();
        
        // Insert after existing content or at the end
        dashboard.appendChild(section);
        
        // Store canvas references
        this.gazeHeatmapCanvas = document.getElementById('gazeHeatmapCanvas');
        this.biometricsCanvas = document.getElementById('biometricsCanvas');
        
        // Add styles
        this.injectStyles();
    }
    
    getPanelHTML() {
        return `
            <div class="analytics-header">
                <h2>
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2zm0 18a8 8 0 1 1 8-8 8 8 0 0 1-8 8z"/>
                        <circle cx="12" cy="12" r="3"/>
                    </svg>
                    Advanced Analytics
                </h2>
                <div class="analytics-status" id="analyticsStatus">
                    <span class="status-dot"></span>
                    <span>Local Processing Active</span>
                </div>
            </div>
            
            <div class="analytics-grid">
                <!-- Biometrics Panel -->
                <div class="analytics-card" id="biometricsPanel">
                    <div class="card-header">
                        <h3>
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M12 11c0 3.517-1.009 6.799-2.753 9.571m-3.44-2.04l.054-.09A13.916 13.916 0 008 11a4 4 0 118 0c0 1.017-.07 2.019-.203 3m-2.118 6.844A21.88 21.88 0 0015.171 17m3.839 1.132c.645-2.266.99-4.659.99-7.132A8 8 0 008 4.07M3 15.364c.64-1.319 1-2.8 1-4.364 0-1.457.39-2.823 1.07-4"/>
                            </svg>
                            Behavioral Biometrics
                        </h3>
                        <span class="card-badge" id="biometricsScore">--</span>
                    </div>
                    <div class="card-body">
                        <canvas id="biometricsCanvas" width="300" height="150"></canvas>
                        <div class="metrics-row">
                            <div class="metric">
                                <span class="metric-label">Identity Match</span>
                                <span class="metric-value" id="identityMatch">--%</span>
                            </div>
                            <div class="metric">
                                <span class="metric-label">Typing Speed</span>
                                <span class="metric-value" id="typingSpeed">-- WPM</span>
                            </div>
                            <div class="metric">
                                <span class="metric-label">Mouse Pattern</span>
                                <span class="metric-value" id="mousePattern">--</span>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Gaze Tracking Panel -->
                <div class="analytics-card" id="gazePanel">
                    <div class="card-header">
                        <h3>
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <circle cx="12" cy="12" r="3"/>
                                <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7z"/>
                            </svg>
                            Gaze Tracking
                        </h3>
                        <span class="card-badge" id="attentionScore">--</span>
                    </div>
                    <div class="card-body">
                        <div class="heatmap-container">
                            <canvas id="gazeHeatmapCanvas" width="200" height="150"></canvas>
                            <div class="heatmap-legend">
                                <span>Low</span>
                                <div class="legend-gradient"></div>
                                <span>High</span>
                            </div>
                        </div>
                        <div class="metrics-row">
                            <div class="metric">
                                <span class="metric-label">Looking at Screen</span>
                                <span class="metric-value" id="lookingAtScreen">--</span>
                            </div>
                            <div class="metric">
                                <span class="metric-label">Distractions</span>
                                <span class="metric-value" id="distractionCount">--</span>
                            </div>
                            <div class="metric">
                                <span class="metric-label">Current Zone</span>
                                <span class="metric-value" id="currentZone">--</span>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Browser Forensics Panel -->
                <div class="analytics-card" id="forensicsPanel">
                    <div class="card-header">
                        <h3>
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <rect x="3" y="4" width="18" height="12" rx="2"/>
                                <line x1="3" y1="20" x2="21" y2="20"/>
                            </svg>
                            Browser Forensics
                        </h3>
                        <span class="card-badge warning" id="forensicsRisk">--</span>
                    </div>
                    <div class="card-body">
                        <div class="forensics-checks">
                            <div class="check-item" id="vmCheck">
                                <span class="check-icon">✓</span>
                                <span>No Virtual Machine</span>
                            </div>
                            <div class="check-item" id="rdCheck">
                                <span class="check-icon">✓</span>
                                <span>No Remote Desktop</span>
                            </div>
                            <div class="check-item" id="extCheck">
                                <span class="check-icon">✓</span>
                                <span>No Suspicious Extensions</span>
                            </div>
                            <div class="check-item" id="shareCheck">
                                <span class="check-icon">✓</span>
                                <span>No Screen Sharing</span>
                            </div>
                        </div>
                        <div class="fingerprint-info" id="fingerprintInfo">
                            <small>Fingerprint: Checking...</small>
                        </div>
                    </div>
                </div>
                
                <!-- Audio Analysis Panel -->
                <div class="analytics-card" id="audioPanel">
                    <div class="card-header">
                        <h3>
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
                                <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
                                <line x1="12" y1="19" x2="12" y2="23"/>
                                <line x1="8" y1="23" x2="16" y2="23"/>
                            </svg>
                            Audio Analysis
                        </h3>
                        <span class="card-badge" id="audioStatus">--</span>
                    </div>
                    <div class="card-body">
                        <div class="audio-visualizer" id="audioVisualizer">
                            <div class="audio-bar" style="height: 20%"></div>
                            <div class="audio-bar" style="height: 40%"></div>
                            <div class="audio-bar" style="height: 60%"></div>
                            <div class="audio-bar" style="height: 35%"></div>
                            <div class="audio-bar" style="height: 25%"></div>
                            <div class="audio-bar" style="height: 50%"></div>
                            <div class="audio-bar" style="height: 30%"></div>
                            <div class="audio-bar" style="height: 45%"></div>
                        </div>
                        <div class="metrics-row">
                            <div class="metric">
                                <span class="metric-label">Voice Detected</span>
                                <span class="metric-value" id="voiceDetected">No</span>
                            </div>
                            <div class="metric">
                                <span class="metric-label">Background</span>
                                <span class="metric-value" id="backgroundNoise">Quiet</span>
                            </div>
                            <div class="metric">
                                <span class="metric-label">Anomalies</span>
                                <span class="metric-value" id="audioAnomalies">0</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Combined Risk Score -->
            <div class="combined-risk-panel" id="combinedRiskPanel">
                <div class="risk-header">
                    <h3>Combined Risk Assessment</h3>
                    <select id="studentSelector" class="student-selector">
                        <option value="">Select Student...</option>
                    </select>
                </div>
                <div class="risk-meter">
                    <div class="risk-bar" id="combinedRiskBar" style="width: 0%"></div>
                </div>
                <div class="risk-value" id="combinedRiskValue">0</div>
                <div class="risk-alerts" id="combinedAlerts">
                    <p>Select a student to view detailed analysis</p>
                </div>
            </div>
        `;
    }
    
    injectStyles() {
        const style = document.createElement('style');
        style.textContent = `
            .advanced-analytics-section {
                margin-top: 2rem;
                padding: 1.5rem;
                background: var(--card-bg, #ffffff);
                border-radius: 12px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }
            
            .analytics-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 1.5rem;
                padding-bottom: 1rem;
                border-bottom: 1px solid var(--border-color, #e5e7eb);
            }
            
            .analytics-header h2 {
                display: flex;
                align-items: center;
                gap: 0.5rem;
                font-size: 1.25rem;
                font-weight: 600;
                color: var(--text-primary, #1f2937);
            }
            
            .analytics-status {
                display: flex;
                align-items: center;
                gap: 0.5rem;
                font-size: 0.875rem;
                color: var(--success-color, #10b981);
            }
            
            .status-dot {
                width: 8px;
                height: 8px;
                background: var(--success-color, #10b981);
                border-radius: 50%;
                animation: pulse 2s infinite;
            }
            
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.5; }
            }
            
            .analytics-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
                gap: 1.5rem;
                margin-bottom: 1.5rem;
            }
            
            .analytics-card {
                background: var(--card-bg-secondary, #f9fafb);
                border-radius: 10px;
                border: 1px solid var(--border-color, #e5e7eb);
                overflow: hidden;
                transition: transform 0.2s, box-shadow 0.2s;
            }
            
            .analytics-card:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
            }
            
            .card-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 1rem;
                background: var(--card-header-bg, #f3f4f6);
                border-bottom: 1px solid var(--border-color, #e5e7eb);
            }
            
            .card-header h3 {
                display: flex;
                align-items: center;
                gap: 0.5rem;
                font-size: 0.9rem;
                font-weight: 600;
                color: var(--text-primary, #1f2937);
            }
            
            .card-badge {
                padding: 0.25rem 0.75rem;
                background: var(--success-color, #10b981);
                color: white;
                border-radius: 20px;
                font-size: 0.75rem;
                font-weight: 600;
            }
            
            .card-badge.warning {
                background: var(--warning-color, #f59e0b);
            }
            
            .card-badge.danger {
                background: var(--danger-color, #ef4444);
            }
            
            .card-body {
                padding: 1rem;
            }
            
            .metrics-row {
                display: flex;
                justify-content: space-between;
                margin-top: 1rem;
                gap: 0.5rem;
            }
            
            .metric {
                text-align: center;
                flex: 1;
            }
            
            .metric-label {
                display: block;
                font-size: 0.7rem;
                color: var(--text-secondary, #6b7280);
                margin-bottom: 0.25rem;
            }
            
            .metric-value {
                font-size: 0.9rem;
                font-weight: 600;
                color: var(--text-primary, #1f2937);
            }
            
            /* Heatmap */
            .heatmap-container {
                text-align: center;
            }
            
            #gazeHeatmapCanvas {
                background: #1a1a2e;
                border-radius: 8px;
            }
            
            .heatmap-legend {
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 0.5rem;
                margin-top: 0.5rem;
                font-size: 0.7rem;
                color: var(--text-secondary, #6b7280);
            }
            
            .legend-gradient {
                width: 60px;
                height: 8px;
                background: linear-gradient(to right, #2196f3, #4caf50, #ffeb3b, #ff9800, #f44336);
                border-radius: 4px;
            }
            
            /* Forensics Checks */
            .forensics-checks {
                display: flex;
                flex-direction: column;
                gap: 0.5rem;
            }
            
            .check-item {
                display: flex;
                align-items: center;
                gap: 0.5rem;
                padding: 0.5rem;
                background: var(--success-bg, rgba(16, 185, 129, 0.1));
                border-radius: 6px;
                font-size: 0.8rem;
            }
            
            .check-item.warning {
                background: var(--warning-bg, rgba(245, 158, 11, 0.1));
            }
            
            .check-item.danger {
                background: var(--danger-bg, rgba(239, 68, 68, 0.1));
            }
            
            .check-icon {
                font-size: 1rem;
                color: var(--success-color, #10b981);
            }
            
            .check-item.warning .check-icon,
            .check-item.danger .check-icon {
                color: var(--danger-color, #ef4444);
            }
            
            .fingerprint-info {
                margin-top: 1rem;
                padding: 0.5rem;
                background: var(--code-bg, #f3f4f6);
                border-radius: 4px;
                font-family: monospace;
                font-size: 0.7rem;
                color: var(--text-secondary, #6b7280);
            }
            
            /* Audio Visualizer */
            .audio-visualizer {
                display: flex;
                align-items: flex-end;
                justify-content: center;
                gap: 4px;
                height: 60px;
                padding: 0.5rem;
                background: #1a1a2e;
                border-radius: 8px;
            }
            
            .audio-bar {
                width: 20px;
                background: linear-gradient(to top, #4caf50, #8bc34a);
                border-radius: 2px 2px 0 0;
                transition: height 0.1s ease;
            }
            
            /* Combined Risk Panel */
            .combined-risk-panel {
                background: var(--card-bg-secondary, #f9fafb);
                border-radius: 10px;
                padding: 1.5rem;
                border: 1px solid var(--border-color, #e5e7eb);
            }
            
            .risk-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 1rem;
            }
            
            .risk-header h3 {
                font-size: 1rem;
                font-weight: 600;
            }
            
            .student-selector {
                padding: 0.5rem 1rem;
                border: 1px solid var(--border-color, #e5e7eb);
                border-radius: 6px;
                background: var(--input-bg, #ffffff);
                font-size: 0.875rem;
            }
            
            .risk-meter {
                height: 20px;
                background: var(--progress-bg, #e5e7eb);
                border-radius: 10px;
                overflow: hidden;
                margin-bottom: 0.5rem;
            }
            
            .risk-bar {
                height: 100%;
                background: linear-gradient(to right, #10b981, #f59e0b, #ef4444);
                border-radius: 10px;
                transition: width 0.5s ease;
            }
            
            .risk-value {
                text-align: center;
                font-size: 2rem;
                font-weight: 700;
                color: var(--text-primary, #1f2937);
            }
            
            .risk-alerts {
                margin-top: 1rem;
                padding: 1rem;
                background: var(--alert-bg, rgba(239, 68, 68, 0.1));
                border-radius: 8px;
                max-height: 150px;
                overflow-y: auto;
            }
            
            .risk-alerts p {
                margin: 0;
                color: var(--text-secondary, #6b7280);
                font-size: 0.875rem;
            }
            
            .alert-item {
                padding: 0.5rem;
                margin-bottom: 0.5rem;
                background: var(--card-bg, #ffffff);
                border-radius: 4px;
                font-size: 0.8rem;
                border-left: 3px solid var(--warning-color, #f59e0b);
            }
            
            /* Dark theme support */
            [data-theme="dark"] .analytics-card,
            [data-theme="dark"] .combined-risk-panel {
                background: #1e293b;
                border-color: #334155;
            }
            
            [data-theme="dark"] .card-header {
                background: #0f172a;
                border-color: #334155;
            }
            
            [data-theme="dark"] .check-item {
                background: rgba(16, 185, 129, 0.15);
            }
            
            [data-theme="dark"] .fingerprint-info {
                background: #0f172a;
            }
        `;
        document.head.appendChild(style);
    }
    
    bindEvents() {
        // Student selector
        const selector = document.getElementById('studentSelector');
        if (selector) {
            selector.addEventListener('change', (e) => {
                this.selectedStudent = e.target.value;
                if (this.selectedStudent) {
                    this.fetchCombinedAnalysis();
                }
            });
        }
    }
    
    // =========================================================================
    // Data Fetching
    // =========================================================================
    
    startAutoRefresh() {
        this.intervalId = setInterval(() => {
            if (this.selectedStudent) {
                this.fetchCombinedAnalysis();
            }
        }, this.refreshInterval);
    }
    
    stopAutoRefresh() {
        if (this.intervalId) {
            clearInterval(this.intervalId);
        }
    }
    
    async fetchCombinedAnalysis() {
        if (!this.selectedStudent) return;
        
        try {
            const response = await fetch(`${this.apiBase}/combined/${this.selectedStudent}`);
            const data = await response.json();
            
            if (data.success) {
                this.updateDashboard(data);
            }
        } catch (error) {
            console.error('[AdvancedAnalytics] Fetch error:', error);
        }
    }
    
    // =========================================================================
    // Dashboard Updates
    // =========================================================================
    
    updateDashboard(data) {
        // Update combined risk
        this.updateCombinedRisk(data.combined_risk_score, data.alerts);
        
        // Update component panels
        if (data.components) {
            this.updateBiometrics(data.components.biometrics);
            this.updateGaze(data.components.gaze);
            this.updateForensics(data.components.forensics);
            this.updateAudio(data.components.audio);
        }
    }
    
    updateCombinedRisk(score, alerts) {
        const riskBar = document.getElementById('combinedRiskBar');
        const riskValue = document.getElementById('combinedRiskValue');
        const alertsContainer = document.getElementById('combinedAlerts');
        
        if (riskBar) {
            riskBar.style.width = `${score}%`;
        }
        
        if (riskValue) {
            riskValue.textContent = Math.round(score);
            
            // Color based on risk
            if (score < 30) {
                riskValue.style.color = '#10b981';
            } else if (score < 60) {
                riskValue.style.color = '#f59e0b';
            } else {
                riskValue.style.color = '#ef4444';
            }
        }
        
        if (alertsContainer && alerts) {
            if (alerts.length > 0) {
                alertsContainer.innerHTML = alerts.map(alert => 
                    `<div class="alert-item">${alert}</div>`
                ).join('');
            } else {
                alertsContainer.innerHTML = '<p>No alerts detected</p>';
            }
        }
    }
    
    updateBiometrics(data) {
        if (!data) return;
        
        const identityMatch = document.getElementById('identityMatch');
        const biometricsScore = document.getElementById('biometricsScore');
        
        if (identityMatch) {
            const match = (data.identity_match * 100).toFixed(0);
            identityMatch.textContent = `${match}%`;
        }
        
        if (biometricsScore) {
            const score = data.risk_score || 0;
            biometricsScore.textContent = `Risk: ${Math.round(score)}`;
            biometricsScore.className = 'card-badge' + 
                (score > 50 ? ' danger' : score > 25 ? ' warning' : '');
        }
    }
    
    updateGaze(data) {
        if (!data) return;
        
        const attentionScore = document.getElementById('attentionScore');
        const lookingAtScreen = document.getElementById('lookingAtScreen');
        const currentZone = document.getElementById('currentZone');
        
        if (attentionScore) {
            const score = data.attention_score || 0;
            attentionScore.textContent = `${Math.round(score)}%`;
            attentionScore.className = 'card-badge' + 
                (score < 50 ? ' danger' : score < 75 ? ' warning' : '');
        }
        
        if (lookingAtScreen) {
            lookingAtScreen.textContent = data.looking_at_screen ? 'Yes ✓' : 'No ✗';
            lookingAtScreen.style.color = data.looking_at_screen ? '#10b981' : '#ef4444';
        }
        
        if (currentZone) {
            currentZone.textContent = data.current_zone || '--';
        }
    }
    
    updateForensics(data) {
        if (!data) return;
        
        const forensicsRisk = document.getElementById('forensicsRisk');
        const vmCheck = document.getElementById('vmCheck');
        const rdCheck = document.getElementById('rdCheck');
        
        if (forensicsRisk) {
            const score = data.risk_score || 0;
            forensicsRisk.textContent = `Risk: ${Math.round(score)}`;
            forensicsRisk.className = 'card-badge' + 
                (score > 50 ? ' danger' : score > 25 ? ' warning' : '');
        }
        
        if (vmCheck) {
            if (data.vm_detected) {
                vmCheck.className = 'check-item danger';
                vmCheck.innerHTML = '<span class="check-icon">✗</span><span>VM Detected!</span>';
            } else {
                vmCheck.className = 'check-item';
                vmCheck.innerHTML = '<span class="check-icon">✓</span><span>No Virtual Machine</span>';
            }
        }
        
        if (rdCheck) {
            if (data.remote_detected) {
                rdCheck.className = 'check-item danger';
                rdCheck.innerHTML = '<span class="check-icon">✗</span><span>Remote Desktop!</span>';
            } else {
                rdCheck.className = 'check-item';
                rdCheck.innerHTML = '<span class="check-icon">✓</span><span>No Remote Desktop</span>';
            }
        }
    }
    
    updateAudio(data) {
        if (!data) return;
        
        const audioStatus = document.getElementById('audioStatus');
        const voiceDetected = document.getElementById('voiceDetected');
        
        if (audioStatus) {
            const score = data.risk_score || 0;
            audioStatus.textContent = score > 30 ? 'Alert' : 'Normal';
            audioStatus.className = 'card-badge' + 
                (score > 50 ? ' danger' : score > 25 ? ' warning' : '');
        }
        
        if (voiceDetected) {
            voiceDetected.textContent = data.voice_detected ? 'Yes' : 'No';
            voiceDetected.style.color = data.voice_detected ? '#f59e0b' : '#10b981';
        }
    }
    
    // =========================================================================
    // Heatmap Rendering
    // =========================================================================
    
    async updateGazeHeatmap() {
        if (!this.selectedStudent || !this.gazeHeatmapCanvas) return;
        
        try {
            const response = await fetch(`${this.apiBase}/gaze/${this.selectedStudent}/heatmap`);
            const data = await response.json();
            
            if (data.heatmap) {
                this.renderHeatmap(data.heatmap.heatmap);
            }
        } catch (error) {
            console.error('[AdvancedAnalytics] Heatmap error:', error);
        }
    }
    
    renderHeatmap(heatmapData) {
        const canvas = this.gazeHeatmapCanvas;
        if (!canvas || !heatmapData) return;
        
        const ctx = canvas.getContext('2d');
        const rows = heatmapData.length;
        const cols = heatmapData[0]?.length || 0;
        
        const cellWidth = canvas.width / cols;
        const cellHeight = canvas.height / rows;
        
        // Clear
        ctx.fillStyle = '#1a1a2e';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        
        // Draw heatmap
        for (let row = 0; row < rows; row++) {
            for (let col = 0; col < cols; col++) {
                const value = heatmapData[row][col];
                const color = this.getHeatmapColor(value);
                
                ctx.fillStyle = color;
                ctx.fillRect(
                    col * cellWidth,
                    row * cellHeight,
                    cellWidth - 1,
                    cellHeight - 1
                );
            }
        }
    }
    
    getHeatmapColor(value) {
        // Blue -> Green -> Yellow -> Orange -> Red
        const colors = [
            [33, 150, 243],   // Blue
            [76, 175, 80],    // Green
            [255, 235, 59],   // Yellow
            [255, 152, 0],    // Orange
            [244, 67, 54],    // Red
        ];
        
        const idx = Math.min(Math.floor(value * (colors.length - 1)), colors.length - 2);
        const t = (value * (colors.length - 1)) - idx;
        
        const r = Math.round(colors[idx][0] + t * (colors[idx + 1][0] - colors[idx][0]));
        const g = Math.round(colors[idx][1] + t * (colors[idx + 1][1] - colors[idx][1]));
        const b = Math.round(colors[idx][2] + t * (colors[idx + 1][2] - colors[idx][2]));
        
        return `rgb(${r}, ${g}, ${b})`;
    }
    
    // =========================================================================
    // Student List
    // =========================================================================
    
    updateStudentList(students) {
        const selector = document.getElementById('studentSelector');
        if (!selector) return;
        
        // Keep current selection
        const current = selector.value;
        
        // Update options
        selector.innerHTML = '<option value="">Select Student...</option>';
        
        students.forEach(student => {
            const option = document.createElement('option');
            option.value = student.id;
            option.textContent = student.name || student.id;
            selector.appendChild(option);
        });
        
        // Restore selection
        if (current) {
            selector.value = current;
        }
    }
}

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Check if we're on the dashboard
    if (document.querySelector('.dashboard-grid') || 
        document.querySelector('.content') ||
        window.location.pathname.includes('dashboard')) {
        
        window.advancedAnalytics = new AdvancedAnalyticsDashboard();
        window.advancedAnalytics.init();
    }
});

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AdvancedAnalyticsDashboard;
}
