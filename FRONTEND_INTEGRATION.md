# Frontend-Backend API Integration Guide

## ✅ Setup Complete

The frontend dashboard is now fully connected to the backend API with comprehensive documentation and client library.

## What Was Created

### 1. **API Client Library** (`dashboard/api-client.js`)
A complete JavaScript library for communicating with the backend API.

**Features**:
- ✅ All session endpoints
- ✅ All event endpoints
- ✅ All report endpoints
- ✅ All upload endpoints
- ✅ Error handling
- ✅ Helper functions for data formatting

### 2. **Updated Dashboard** (`dashboard/index.html` & `dashboard/app.js`)
- ✅ Integrated API client
- ✅ Real-time server status monitoring
- ✅ Dynamic session loading from API
- ✅ Report generation and downloads
- ✅ Event timeline viewing
- ✅ Better error messages

### 3. **API Documentation** (`API_DOCUMENTATION.md`)
Complete reference with:
- ✅ All endpoints documented
- ✅ Request/response examples
- ✅ JavaScript usage examples
- ✅ Error handling guide
- ✅ Complete workflow examples

## Quick Start

### 1. Start the Backend Server
```bash
cd server
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

### 2. Open Dashboard
```
Open: dashboard/index.html in your browser
Or: http://localhost:3000 (if running with a web server)
```

### 3. Access API Documentation
```
http://localhost:8000/docs (Interactive Swagger UI)
```

## API Endpoints Reference

### Sessions
```javascript
// Start exam session
await startSession({
  student_id: 'STU001',
  student_name: 'John Doe',
  exam_id: 'EXAM-CS101'
});

// Get all sessions
await getAllSessions();

// Get session details
await getSessionDetails(sessionId);

// End session
await endSession(sessionId);
```

### Events
```javascript
// Log single event
await logEvent({
  session_id: sessionId,
  type: 'TAB_SWITCH',
  timestamp: Date.now(),
  data: { tab_title: 'GitHub' }
});

// Log batch of events
await logEventsBatch(eventsArray);

// Get session events
await getSessionEvents(sessionId);
```

### Reports
```javascript
// Get report summary
await getReportSummary(sessionId);

// Get JSON report
await getJSONReport(sessionId);

// Download PDF report
await downloadPDFReport(sessionId);
```

### Uploads
```javascript
// Upload screenshot
await uploadScreenshot({
  session_id: sessionId,
  timestamp: Date.now(),
  image_data: base64ImageData
});

// Upload webcam frame
await uploadWebcamFrame({
  session_id: sessionId,
  timestamp: Date.now(),
  image_data: base64ImageData
});
```

## Dashboard Features

### 📊 Dashboard View
- Real-time statistics
- Active sessions count
- Risk level overview
- Recent sessions list

### 📝 Sessions View
- Complete list of all exams
- Filter by exam or status
- Session details on click
- Risk indicators

### 🚨 Flagged Sessions
- Sessions requiring review
- High-risk indicators
- Quick report access

### ⚙️ Settings
- API URL configuration
- Risk threshold adjustment
- Settings persistence

## Configuration

### API Base URL
The dashboard automatically connects to:
```
http://localhost:8000/api
```

To change, edit in `dashboard/api-client.js`:
```javascript
const API_CONFIG = {
    BASE_URL: 'http://localhost:8000/api',
    // ...
};
```

Or set in browser console:
```javascript
localStorage.setItem('api_url', 'http://your-server:8000/api');
```

## Error Handling

The dashboard includes comprehensive error handling:

```javascript
// All API calls return consistent format
const result = await getAllSessions();

if (result.success) {
  // Use result.data
  console.log(result.data);
} else {
  // Handle error
  console.error('Error:', result.error);
}
```

## File Structure

```
dashboard/
├── index.html           # Main UI
├── app.js              # Application logic
├── api-client.js       # API communication library (NEW)
├── styles.css          # Styling
└── API integration complete ✅
```

## Testing the Connection

### Test 1: Check Server Status
```javascript
const health = await checkAPIHealth();
console.log(health.success ? '✅ Server Online' : '❌ Server Offline');
```

### Test 2: Load Sessions
```javascript
const result = await getAllSessions();
console.log(`Found ${result.data.data.length} sessions`);
```

### Test 3: Create Session
```javascript
const result = await startSession({
  student_id: 'TEST001',
  student_name: 'Test Student',
  exam_id: 'TEST-EXAM'
});
console.log('Session Created:', result.data.session_id);
```

## Browser Console Testing

Open the browser's developer console (F12) and try:

```javascript
// Check API health
await checkAPIHealth();

// Get all sessions
const result = await getAllSessions();
console.log(result);

// Start a test session
const session = await startSession({
  student_id: 'TEST001',
  student_name: 'Test User',
  exam_id: 'TEST-100'
});
console.log(session);
```

## Integration Points

### Session Management
- Dashboard loads sessions from API on page load
- Sessions refresh every 30 seconds
- Click session to view details from API

### Event Logging
- Events logged automatically by Chrome extension
- Batch logging for efficiency
- Real-time risk score updates

### Report Generation
- One-click report download (PDF or JSON)
- Event timeline viewing
- Risk analysis display

## Troubleshooting

### "Server Offline" Message
- Check backend is running: `python -m uvicorn main:app --host 0.0.0.0 --port 8000`
- Check port 8000 is available
- Check firewall settings

### Sessions Not Loading
- Verify API is responding: `curl http://localhost:8000/health`
- Check browser console for errors (F12)
- Verify correct API URL in settings

### CORS Errors
- Backend already has CORS enabled
- Check browser console for details
- Ensure making requests to `http://localhost:8000/api`

## Next Steps

1. **Test the API**
   - Open dashboard in browser
   - Click "Refresh" button
   - Should show "🟢 Server Online"

2. **Create a Test Session**
   - In browser console: `startSession({...})`
   - Verify it appears in dashboard

3. **Log Test Events**
   - Use `logEvent()` or `logEventsBatch()`
   - Check event appears in timeline

4. **Generate Reports**
   - Click "Download Report" button
   - Download PDF or JSON

## Support

For API reference, see:
- **[API_DOCUMENTATION.md](../API_DOCUMENTATION.md)** - Complete endpoint documentation
- **[api-client.js](./api-client.js)** - Source code with comments
- **Dashboard** - Interactive testing interface

---

**Integration Status**: ✅ Complete  
**Frontend**: ✅ Connected to Backend  
**API Client**: ✅ Full Featured  
**Documentation**: ✅ Comprehensive  
**Date**: January 25, 2026
