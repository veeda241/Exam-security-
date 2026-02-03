# ExamGuard Pro - Quick Start Guide

## ✅ Status: Application Ready to Run

All errors have been fixed and the application is fully functional.

### Server Status
- **Backend API**: ✅ Running on `http://0.0.0.0:8000`
- **Database**: ✅ SQLite initialized and ready
- **All Modules**: ✅ Successfully loaded
- **Dependencies**: ✅ All installed

### Quick Start

#### Option 1: Windows Batch Script (Recommended)
```bash
start_server.bat
```

#### Option 2: Manual Start (Server only)
```bash
cd server
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

#### Option 3: With Auto-Reload (Development)
```bash
cd server
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Available Endpoints

#### Health Check
- **GET** `/` - Root health check
- **GET** `/health` - Detailed health check
- **GET** `/docs` - Interactive API documentation (Swagger UI)

#### Sessions API
- **POST** `/api/sessions/start` - Start a new exam session
- **GET** `/api/sessions/{session_id}` - Get session details
- **POST** `/api/sessions/{session_id}/end` - End an exam session
- **GET** `/api/sessions` - List all sessions

#### Events API
- **POST** `/api/events/log` - Log a single event
- **POST** `/api/events/batch` - Log multiple events

#### Uploads API
- **POST** `/api/uploads/screenshot` - Upload screenshot for analysis
- **POST** `/api/uploads/webcam` - Upload webcam frame

#### Reports API
- **GET** `/api/reports/session/{session_id}/summary` - Get report summary
- **GET** `/api/reports/session/{session_id}/json` - Get full JSON report
- **GET** `/api/reports/session/{session_id}/download` - Download PDF report

### Testing the Application

#### Test API Health
```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "database": "connected",
  "ai_modules": {
    "face_detection": "ready",
    "ocr": "ready",
    "text_similarity": "ready",
    "anomaly_detection": "ready"
  }
}
```

### Project Structure

```
Exam-security/
├── server/               # FastAPI backend
│   ├── main.py          # Application entry point
│   ├── config.py        # Configuration settings
│   ├── database.py      # Database setup
│   ├── requirements.txt  # Python dependencies
│   ├── api/             # API endpoints
│   ├── models/          # Database models
│   ├── analysis/        # AI analysis modules
│   ├── scoring/         # Risk scoring system
│   └── reports/         # Report generation
├── dashboard/           # Teacher dashboard UI
│   ├── index.html
│   ├── app.js
│   └── styles.css
├── extension/           # Chrome extension
│   ├── manifest.json
│   ├── background.js
│   ├── popup/
│   └── icons/
└── README.md
```

### Key Features Implemented

✅ **Session Management**
- Start/stop exam sessions
- Track student information
- Calculate risk scores in real-time

✅ **Event Logging**
- Tab switches detection
- Copy/paste detection
- Window focus tracking
- Page visibility changes

✅ **Analysis Modules**
- Face detection (webcam)
- OCR for text extraction
- Text similarity checking
- Anomaly detection

✅ **Risk Scoring**
- Weighted event scoring
- Risk level classification
- Threshold-based alerts

✅ **Reporting**
- JSON reports
- PDF reports (when ReportLab is installed)
- Event timeline
- Risk analysis

### Installing Optional Dependencies

For enhanced PDF report generation:
```bash
pip install reportlab
```

For image processing (face detection, OCR):
```bash
pip install opencv-python mediapipe pytesseract
```

### Database

The application uses SQLite for simplicity. Database file: `server/examguard.db`

**Tables Created:**
- `exam_sessions` - Session records
- `events` - Logged events
- `analysis_results` - AI analysis results

### Troubleshooting

**Port Already in Use**
```bash
# Change port in the command
python -m uvicorn main:app --host 0.0.0.0 --port 8001
```

**Database Issues**
```bash
# Delete the database to reset
rm server/examguard.db
# Then restart the server
```

**Module Import Errors**
```bash
# Reinstall dependencies
pip install -r server/requirements.txt
```

### Configuration

Edit `server/config.py` to customize:
- Screenshot interval
- Webcam interval
- Forbidden keywords
- Risk score weights
- Face detection thresholds
- OCR language
- Text similarity threshold

---

**Status**: ✅ All systems operational
**Last Updated**: January 25, 2026
**Version**: 1.0.0
