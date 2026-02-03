# ExamGuard Pro - API Documentation

## Overview

Complete REST API documentation for ExamGuard Pro backend. The API is built with FastAPI and provides endpoints for session management, event logging, file uploads, and report generation.

**Base URL**: `http://localhost:8000/api`

## Quick Start

### Server Health Check
```bash
# Check if server is running
curl http://localhost:8000/health
```

**Response** (Success):
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

---

## Sessions API

### Start a New Session
**POST** `/api/sessions/start`

Start a new exam session with student information.

**Request Body**:
```json
{
  "student_id": "STU001",
  "student_name": "John Doe",
  "exam_id": "EXAM-CS101"
}
```

**Response** (201):
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "student_id": "STU001",
  "student_name": "John Doe",
  "exam_id": "EXAM-CS101",
  "started_at": "2026-01-25T10:30:00Z",
  "is_active": true,
  "risk_score": 0.0
}
```

**Usage Example** (JavaScript):
```javascript
const result = await startSession({
  student_id: 'STU001',
  student_name: 'John Doe',
  exam_id: 'EXAM-CS101'
});

if (result.success) {
  const sessionId = result.data.session_id;
  console.log('Session started:', sessionId);
}
```

---

### Get All Sessions
**GET** `/api/sessions`

Retrieve all exam sessions.

**Query Parameters**:
- `limit` (optional): Number of sessions to return (default: 100)
- `offset` (optional): Pagination offset (default: 0)

**Response** (200):
```json
{
  "data": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "student_id": "STU001",
      "student_name": "John Doe",
      "exam_id": "EXAM-CS101",
      "started_at": "2026-01-25T10:30:00Z",
      "ended_at": null,
      "is_active": true,
      "risk_score": 15.5,
      "risk_level": "safe",
      "total_events": 25
    }
  ],
  "total": 1
}
```

**Usage Example**:
```javascript
const result = await getAllSessions();
if (result.success) {
  result.data.data.forEach(session => {
    console.log(`${session.student_name}: Risk ${session.risk_score}`);
  });
}
```

---

### Get Session Details
**GET** `/api/sessions/{session_id}`

Retrieve detailed information for a specific session.

**Path Parameters**:
- `session_id` (required): Session ID

**Response** (200):
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "student_id": "STU001",
  "student_name": "John Doe",
  "exam_id": "EXAM-CS101",
  "started_at": "2026-01-25T10:30:00Z",
  "ended_at": null,
  "is_active": true,
  "risk_score": 15.5,
  "risk_level": "safe",
  "tab_switch_count": 3,
  "copy_count": 1,
  "face_absence_count": 0,
  "forbidden_site_count": 0,
  "total_events": 25
}
```

**Usage Example**:
```javascript
const result = await getSessionDetails('550e8400-e29b-41d4-a716-446655440000');
if (result.success) {
  console.log('Risk Level:', result.data.risk_level);
}
```

---

### End Session
**POST** `/api/sessions/{session_id}/end`

End an active exam session.

**Response** (200):
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Session ended successfully",
  "total_events": 50,
  "final_risk_score": 25.0
}
```

**Usage Example**:
```javascript
await endSession('550e8400-e29b-41d4-a716-446655440000');
```

---

## Events API

### Log Single Event
**POST** `/api/events/log`

Log a single event from the exam session.

**Request Body**:
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "type": "TAB_SWITCH",
  "timestamp": 1674641400000,
  "data": {
    "tab_title": "GitHub",
    "tab_url": "https://github.com"
  }
}
```

**Event Types**:
- `TAB_SWITCH` - Student switched tabs (Risk: 10)
- `WINDOW_BLUR` - Browser window lost focus (Risk: 5)
- `COPY` - Copy event detected (Risk: 15)
- `PASTE` - Paste event detected (Risk: 10)
- `FORBIDDEN_SITE` - Forbidden website accessed (Risk: 40)
- `FORBIDDEN_CONTENT` - Forbidden content detected (Risk: 40)
- `FACE_ABSENT` - Face not detected in webcam (Risk: 20)
- `SUSPICIOUS_SHORTCUT` - Suspicious keyboard shortcut (Risk: 15)
- `CONTEXT_MENU` - Right-click context menu (Risk: 5)
- `PAGE_HIDDEN` - Page visibility changed (Risk: 8)
- `SCREEN_SHARE_STOPPED` - Screen sharing ended (Risk: 50)

**Response** (201):
```json
{
  "id": "event-001",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "event_type": "TAB_SWITCH",
  "timestamp": "2026-01-25T10:30:00Z",
  "risk_weight": 10
}
```

**Usage Example**:
```javascript
const result = await logEvent({
  session_id: 'session-123',
  type: 'TAB_SWITCH',
  timestamp: Date.now(),
  data: { tab_title: 'Stack Overflow' }
});
```

---

### Log Multiple Events (Batch)
**POST** `/api/events/batch`

Log multiple events in one request for efficiency.

**Request Body**:
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "events": [
    {
      "type": "TAB_SWITCH",
      "timestamp": 1674641400000,
      "data": { "tab_title": "GitHub" }
    },
    {
      "type": "COPY",
      "timestamp": 1674641410000,
      "data": {}
    }
  ]
}
```

**Response** (200):
```json
{
  "logged": 2,
  "failed": 0,
  "message": "Successfully logged 2 events"
}
```

**Usage Example**:
```javascript
const events = [
  { type: 'TAB_SWITCH', timestamp: Date.now(), data: {} },
  { type: 'COPY', timestamp: Date.now(), data: {} }
];

const result = await logEventsBatch(events);
```

---

### Get Session Events
**GET** `/api/events/session/{session_id}`

Get all events for a specific session.

**Response** (200):
```json
{
  "data": [
    {
      "id": "event-001",
      "session_id": "550e8400-e29b-41d4-a716-446655440000",
      "event_type": "TAB_SWITCH",
      "timestamp": "2026-01-25T10:30:00Z",
      "risk_weight": 10,
      "data": { "tab_title": "GitHub" }
    }
  ],
  "total": 25
}
```

**Usage Example**:
```javascript
const result = await getSessionEvents('550e8400-e29b-41d4-a716-446655440000');
if (result.success) {
  console.log(`Total events: ${result.data.total}`);
}
```

---

## Reports API

### Get Report Summary
**GET** `/api/reports/session/{session_id}/summary`

Get a summary report for an exam session.

**Response** (200):
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "student_name": "John Doe",
  "exam_id": "EXAM-CS101",
  "duration_seconds": 3600,
  "risk_score": 25.5,
  "risk_level": "review",
  "event_counts": {
    "tab_switches": 5,
    "copy_events": 2,
    "face_absences": 0,
    "forbidden_sites": 0,
    "total": 25
  },
  "high_risk_events": [
    {
      "event_type": "TAB_SWITCH",
      "timestamp": "2026-01-25T10:35:00Z",
      "risk_weight": 10
    }
  ]
}
```

**Usage Example**:
```javascript
const result = await getReportSummary('550e8400-e29b-41d4-a716-446655440000');
if (result.success) {
  console.log('Risk Level:', result.data.risk_level);
}
```

---

### Get JSON Report
**GET** `/api/reports/session/{session_id}/json`

Get complete JSON report with all session data.

**Response** (200):
```json
{
  "session": { ... },
  "events": [ ... ],
  "analysis_results": [ ... ],
  "statistics": { ... }
}
```

**Usage Example**:
```javascript
const result = await getJSONReport('550e8400-e29b-41d4-a716-446655440000');
if (result.success) {
  // Save to file
  const blob = new Blob([JSON.stringify(result.data, null, 2)]);
  // Download blob...
}
```

---

### Download PDF Report
**GET** `/api/reports/session/{session_id}/download`

Download a PDF report (requires ReportLab).

**Response**: PDF file

**Usage Example**:
```javascript
downloadPDFReport('550e8400-e29b-41d4-a716-446655440000');
// Browser will download the PDF automatically
```

---

## Uploads API

### Upload Screenshot
**POST** `/api/uploads/screenshot`

Upload a screenshot for OCR analysis.

**Request Body**:
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": 1674641400000,
  "image_data": "data:image/jpeg;base64,/9j/4AAQSkZJRgABA..."
}
```

**Response** (200):
```json
{
  "success": true,
  "file_id": "ss_550e8400_1674641400000_abc123",
  "analysis_triggered": true
}
```

**Usage Example**:
```javascript
// Capture canvas to base64
canvas.toBlob(blob => {
  const reader = new FileReader();
  reader.onload = async (e) => {
    const result = await uploadScreenshot({
      session_id: 'session-123',
      timestamp: Date.now(),
      image_data: e.target.result
    });
  };
  reader.readAsDataURL(blob);
});
```

---

### Upload Webcam Frame
**POST** `/api/uploads/webcam`

Upload a webcam frame for face detection.

**Request Body**:
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": 1674641400000,
  "image_data": "data:image/jpeg;base64,/9j/4AAQSkZJRgABA..."
}
```

**Response** (200):
```json
{
  "success": true,
  "file_id": "wc_550e8400_1674641400000_xyz789",
  "analysis_triggered": true,
  "face_detected": true
}
```

**Usage Example**:
```javascript
const result = await uploadWebcamFrame({
  session_id: 'session-123',
  timestamp: Date.now(),
  image_data: base64ImageData
});
```

---

## Error Handling

All API responses include status information.

### Success Response
```json
{
  "success": true,
  "data": { ... }
}
```

### Error Response
```json
{
  "success": false,
  "error": "Error message describing what went wrong"
}
```

### Common HTTP Status Codes
- `200` - OK
- `201` - Created
- `400` - Bad Request
- `404` - Not Found
- `500` - Server Error

### Error Handling in JavaScript
```javascript
const result = await getAllSessions();

if (!result.success) {
  console.error('API Error:', result.error);
  // Handle error
} else {
  // Use result.data
}
```

---

## Rate Limiting

No rate limiting is currently enforced, but please use reasonable request frequencies to avoid overloading the server.

---

## Authentication

Currently, the API does not require authentication. In production, implement API keys or OAuth.

---

## CORS

CORS is enabled for all origins. In production, restrict to specific domains:

```python
# In server/main.py
allow_origins=[
    "http://localhost:3000",
    "https://yourdomain.com"
]
```

---

## Example: Complete Exam Session

```javascript
// 1. Start session
const startResult = await startSession({
  student_id: 'STU001',
  student_name: 'John Doe',
  exam_id: 'EXAM-CS101'
});
const sessionId = startResult.data.session_id;

// 2. Log events during exam
await logEvent({
  session_id: sessionId,
  type: 'TAB_SWITCH',
  timestamp: Date.now(),
  data: { tab_title: 'GitHub' }
});

// 3. Upload screenshots periodically
await uploadScreenshot({
  session_id: sessionId,
  timestamp: Date.now(),
  image_data: screenshotBase64
});

// 4. Upload webcam frames
await uploadWebcamFrame({
  session_id: sessionId,
  timestamp: Date.now(),
  image_data: webcamBase64
});

// 5. End session
await endSession(sessionId);

// 6. Generate report
const reportResult = await getReportSummary(sessionId);
console.log('Risk Score:', reportResult.data.risk_score);

// 7. Download PDF report
downloadPDFReport(sessionId);
```

---

## API Response Examples

All responses follow consistent JSON structure for easy integration.

**Session Creation Success**:
```json
{
  "success": true,
  "data": {
    "session_id": "uuid-here",
    "student_name": "John Doe",
    "is_active": true,
    "risk_score": 0.0
  }
}
```

**Session Retrieval**:
```json
{
  "success": true,
  "data": {
    "data": [
      { "session1_data": "..." },
      { "session2_data": "..." }
    ],
    "total": 2
  }
}
```

**Event Logging**:
```json
{
  "success": true,
  "data": {
    "id": "event-id",
    "session_id": "session-id",
    "event_type": "TAB_SWITCH",
    "risk_weight": 10
  }
}
```

---

## Troubleshooting

### Server Not Responding
```
Error: Failed to connect to http://localhost:8000
Solution: Ensure the backend server is running
Run: python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

### Database Connection Error
```
Error: Database connection failed
Solution: Delete examguard.db and restart the server
```

### CORS Error
```
Error: Access to XMLHttpRequest blocked by CORS
Solution: Check server CORS configuration in main.py
```

---

**API Version**: 1.0.0  
**Last Updated**: January 25, 2026  
**Status**: ✅ Production Ready
