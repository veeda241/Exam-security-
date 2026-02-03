# ExamGuard Pro - API Documentation

## Overview

The `api/` folder contains a well-organized API structure with clear separation of concerns:

```
api/
├── __init__.py          # Package exports and registration
├── router.py            # Router registration helper
├── dependencies.py      # Shared FastAPI dependencies
├── utils.py             # Utility functions
├── models/              # SQLAlchemy database models
├── schemas/             # Pydantic request/response schemas
└── endpoints/           # FastAPI route handlers
```

## Structure Details

### Models (`models/`)

SQLAlchemy ORM models representing database tables:

| File | Model | Description |
|------|-------|-------------|
| `student.py` | `Student` | Exam taker information |
| `session.py` | `ExamSession` | Exam session with scores and stats |
| `event.py` | `Event` | Proctoring events (tab switches, copies, etc.) |
| `analysis.py` | `AnalysisResult` | AI analysis results (face, OCR, similarity) |
| `research.py` | `ResearchJourney`, `SearchStrategy` | Research path tracking |

### Schemas (`schemas/`)

Pydantic models for request validation and response serialization:

| File | Schemas | Purpose |
|------|---------|---------|
| `student.py` | `StudentCreate`, `StudentResponse`, `StudentSummary` | Student CRUD operations |
| `session.py` | `SessionCreate`, `SessionResponse`, `SessionSummary` | Session management |
| `event.py` | `EventData`, `EventBatch`, `EventResponse` | Event logging |
| `analysis.py` | `AnalysisRequest`, `TextAnalysisRequest`, `PlagiarismCheckRequest` | AI analysis |
| `report.py` | `ReportRequest`, `ReportSummary`, `ReportResponse` | Report generation |
| `upload.py` | `ImageUpload`, `UploadResponse` | File uploads |

### Endpoints (`endpoints/`)

FastAPI route handlers organized by domain:

| File | Prefix | Description |
|------|--------|-------------|
| `students.py` | `/api/students` | Student CRUD operations |
| `sessions.py` | `/api/sessions` | Exam session management |
| `events.py` | `/api/events` | Event logging and retrieval |
| `analysis.py` | `/api/analysis` | AI-powered analysis |
| `uploads.py` | `/api/uploads` | Screenshot/webcam uploads |
| `reports.py` | `/api/reports` | Report generation |
| `research.py` | `/api/research` | Research journey analysis |
| `transformer.py` | `/api/transformer` | Transformer-based text analysis |

## Usage

### Registering Routers

In your `main.py`:

```python
from fastapi import FastAPI
from api import register_all_routers

app = FastAPI(title="ExamGuard Pro")

# Register all API routers
register_all_routers(app)
```

### Using Models

```python
from api.models import Student, ExamSession, Event

# Create a new student
student = Student(name="John Doe", email="john@example.com")
```

### Using Schemas

```python
from api.schemas import StudentCreate, SessionCreate

# Validate request data
student_data = StudentCreate(name="John", email="john@example.com")
```

### Using Dependencies

```python
from fastapi import Depends
from api.dependencies import get_current_session, get_pagination

@router.get("/items")
async def list_items(pagination = Depends(get_pagination)):
    return {"skip": pagination.skip, "limit": pagination.limit}
```

### Using Utilities

```python
from api.utils import decode_base64_image, calculate_risk_level, ResponseBuilder

# Decode image
image = decode_base64_image(base64_string)

# Get risk level
level = calculate_risk_level(75.5)  # Returns "suspicious"

# Build response
response = ResponseBuilder.success(data={"id": "123"})
```

## API Endpoints Reference

### Students API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/students/` | Create new student |
| GET | `/api/students/` | List all students |
| GET | `/api/students/{id}` | Get student by ID |
| PUT | `/api/students/{id}` | Update student |
| DELETE | `/api/students/{id}` | Delete student |

### Sessions API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/sessions/create` | Create new session |
| POST | `/api/sessions/{id}/end` | End session |
| GET | `/api/sessions/{id}` | Get session details |
| GET | `/api/sessions/` | List all sessions |

### Events API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/events/log` | Log single event |
| POST | `/api/events/batch` | Log batch of events |
| GET | `/api/events/session/{id}` | Get session events |
| GET | `/api/events/session/{id}/timeline` | Get event timeline |

### Analysis API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/analysis/process` | Process webcam/screen data |
| GET | `/api/analysis/dashboard` | Get dashboard data |
| GET | `/api/analysis/student/{id}` | Get student analysis |
| GET | `/api/analysis/stats` | Get overall stats |

### Transformer API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/transformer/similarity` | Check text similarity |
| POST | `/api/transformer/plagiarism` | Detect plagiarism |
| POST | `/api/transformer/cross-compare` | Compare multiple answers |
| GET | `/api/transformer/status` | Get analyzer status |

### Uploads API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/uploads/screenshot` | Upload screenshot |
| POST | `/api/uploads/webcam` | Upload webcam frame |
| DELETE | `/api/uploads/cleanup/{id}` | Cleanup session files |

### Reports API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/reports/session/{id}/summary` | Get session summary |
| GET | `/api/reports/session/{id}/json` | Get full JSON report |
| GET | `/api/reports/session/{id}/pdf` | Download PDF report |
| GET | `/api/reports/session/{id}/timeline` | Get event timeline |

### Research API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/research/session/{id}/analysis` | Get research analysis |
| GET | `/api/research/session/{id}/journey` | Get research journey |
| GET | `/api/research/session/{id}/strategy` | Get search strategy |
| POST | `/api/research/session/{id}/analyze` | Trigger analysis |

## Error Handling

All endpoints return consistent error responses:

```json
{
    "detail": "Error message here"
}
```

Common HTTP status codes:
- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `404` - Not Found
- `422` - Validation Error
- `500` - Internal Server Error
