"""
ExamGuard Pro - Pydantic Schemas
Request/Response models for API endpoints
"""

from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime


# ==================== Student Schemas ====================

class StudentCreate(BaseModel):
    name: str
    email: EmailStr


class StudentResponse(BaseModel):
    id: str
    name: str
    email: str
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== Session Schemas ====================

class SessionCreate(BaseModel):
    student_id: str
    student_name: str
    exam_id: str


class SessionResponse(BaseModel):
    session_id: str
    student_id: str
    student_name: str
    exam_id: str
    started_at: str
    is_active: bool


class SessionSummary(BaseModel):
    id: str
    student_name: str
    student_id: str
    exam_id: str
    started_at: str
    ended_at: Optional[str]
    risk_score: float
    risk_level: str
    engagement_score: float
    content_relevance: float
    effort_alignment: float
    status: str
    stats: dict


# ==================== Event Schemas ====================

class EventCreate(BaseModel):
    session_id: str
    event_type: str
    data: Dict[str, Any] = {}
    timestamp: Optional[int] = None


class EventBatch(BaseModel):
    session_id: str
    events: List[Dict[str, Any]]


class EventResponse(BaseModel):
    id: str
    session_id: str
    event_type: str
    timestamp: datetime
    data: dict

    class Config:
        from_attributes = True


# ==================== Analysis Schemas ====================

class AnalysisRequest(BaseModel):
    session_id: str
    webcam_image: Optional[str] = None  # Base64
    screen_image: Optional[str] = None  # Base64
    clipboard_text: Optional[str] = None
    timestamp: int


class AnalysisResponse(BaseModel):
    status: str
    risk_score: float
    face_detected: Optional[bool] = None
    forbidden_detected: Optional[bool] = None
    similarity_score: Optional[float] = None


class DashboardStats(BaseModel):
    total_students: int
    active_sessions: int
    average_engagement: float
    high_risk_count: int


class StudentSummary(BaseModel):
    student_id: str
    name: str
    email: str
    latest_session_id: Optional[str]
    risk_score: float
    engagement_score: float
    effort_alignment: float
    status: str


# ==================== Report Schemas ====================

class ReportRequest(BaseModel):
    session_id: str
    include_events: bool = True
    include_analysis: bool = True


class ReportResponse(BaseModel):
    session: SessionSummary
    events: Optional[List[EventResponse]] = None
    analysis_results: Optional[List[dict]] = None
    summary: dict
