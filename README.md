# ExamGuard Pro - Exam Proctoring System

A comprehensive exam security and proctoring solution with real-time monitoring, AI-powered analysis, and automated risk scoring.

## ✅ Status: Ready to Run

All errors have been fixed and the application is fully operational.

## Quick Start

### Windows Users
```bash
start_server.bat
```

### Manual Start
```bash
cd server
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

The API will be available at: **http://localhost:8000**

## Features

### 🛡️ Security Monitoring
- **Real-time Activity Tracking**: Monitor tab switches, window focus, copy/paste events
- **Face Detection**: Verify student presence using webcam
- **Screenshot Analysis**: OCR-based forbidden content detection
- **Anomaly Detection**: AI-powered suspicious behavior identification

### 📊 Risk Scoring System
- **Weighted Event Scoring**: Different event types have different risk weights
- **Dynamic Risk Levels**: Safe, Review, Suspicious classifications
- **Cumulative Risk Analysis**: Track risk over time

### 📋 Session Management
- **Session Control**: Start, monitor, and end exam sessions
- **Student Information**: Track student ID, name, exam code
- **Event Logging**: Comprehensive event history with timestamps

### 📈 Reporting
- **JSON Reports**: Structured data export
- **PDF Reports**: Professional formatted reports (with reportlab)
- **Risk Analysis**: Event timeline with risk contributions

### 🔌 Chrome Extension
- **Seamless Integration**: Monitors exam activity in real-time
- **Automatic Capture**: Periodic screenshots and webcam frames
- **Event Logging**: Sends all events to backend

### 👨‍🏫 Teacher Dashboard
- **Session Overview**: View all active sessions
- **Risk Alerts**: Immediate flagging of suspicious activity
- **Report Generation**: Create detailed reports

## Installation

1. **Install Dependencies**
   ```bash
   cd server
   pip install -r requirements.txt
   ```

2. **Start Server**
   ```bash
   python -m uvicorn main:app --host 0.0.0.0 --port 8000
   ```

3. **Access Dashboard**
   - Open `dashboard/index.html` in your browser

4. **Install Chrome Extension**
   - Go to `chrome://extensions`
   - Enable "Developer mode"
   - Click "Load unpacked"
   - Select `extension/` folder

## Documentation

- **QUICKSTART.md** - Quick start guide
- **VERIFICATION_REPORT.md** - Detailed verification report

## License

MIT License

---

**Status**: ✅ Ready to Run  
**Version**: 1.0.0  
**All Systems**: Operational
