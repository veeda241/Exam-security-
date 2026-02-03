"""
ExamGuard Pro - API Schemas Package
Pydantic request/response models for all endpoints
"""

from .student import (
    StudentCreate,
    StudentUpdate,
    StudentResponse,
    StudentSummary
)
from .session import (
    SessionCreate,
    SessionResponse,
    SessionSummary,
    SessionUpdate
)
from .event import (
    EventCreate,
    EventData,
    EventBatch,
    EventResponse
)
from .analysis import (
    AnalysisRequest,
    AnalysisResponse,
    TextAnalysisRequest,
    PlagiarismCheckRequest,
    MultiAnswerRequest,
    DashboardStats
)
from .report import (
    ReportRequest,
    ReportResponse,
    ReportSummary
)
from .upload import (
    ImageUpload,
    UploadResponse
)

__all__ = [
    # Student
    "StudentCreate",
    "StudentUpdate", 
    "StudentResponse",
    "StudentSummary",
    # Session
    "SessionCreate",
    "SessionResponse",
    "SessionSummary",
    "SessionUpdate",
    # Event
    "EventCreate",
    "EventData",
    "EventBatch",
    "EventResponse",
    # Analysis
    "AnalysisRequest",
    "AnalysisResponse",
    "TextAnalysisRequest",
    "PlagiarismCheckRequest",
    "MultiAnswerRequest",
    "DashboardStats",
    # Report
    "ReportRequest",
    "ReportResponse",
    "ReportSummary",
    # Upload
    "ImageUpload",
    "UploadResponse"
]
