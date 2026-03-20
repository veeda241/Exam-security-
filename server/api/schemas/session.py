"""
ExamGuard Pro - Session Schemas
Pydantic models for exam session requests/responses
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class SessionCreate(BaseModel):
    """Schema for creating a new exam session"""
    student_id: str = Field(..., description="Student's unique identifier")
    student_name: str = Field(..., min_length=1, max_length=255, description="Student's name")
    student_email: Optional[str] = Field(None, description="Student's email address")
    exam_id: str = Field(..., description="Exam identifier")
    
    class Config:
        json_schema_extra = {
            "example": {
                "student_id": "student-123",
                "student_name": "John Doe",
                "exam_id": "midterm-2026"
            }
        }


class SessionResponse(BaseModel):
    """Schema for session creation response"""
    session_id: str
    student_id: str
    student_name: str
    exam_id: str
    started_at: str
    is_active: bool = True


class SessionUpdate(BaseModel):
    """Schema for updating session status"""
    is_active: Optional[bool] = None
    risk_score: Optional[float] = None
    risk_level: Optional[str] = None
    engagement_score: Optional[float] = None
    content_relevance: Optional[float] = None
    effort_alignment: Optional[float] = None


class SessionSummary(BaseModel):
    """Schema for detailed session information"""
    id: str
    student_name: str
    student_id: str
    exam_id: str
    started_at: str
    ended_at: Optional[str] = None
    risk_score: Optional[float] = 0.0
    risk_level: Optional[str] = "safe"
    engagement_score: Optional[float] = 100.0
    content_relevance: Optional[float] = 100.0
    effort_alignment: Optional[float] = 100.0
    status: Optional[str] = "active"
    stats: Optional[Dict[str, Any]] = {}
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "session-123",
                "student_name": "John Doe",
                "student_id": "student-123",
                "exam_id": "midterm-2026",
                "started_at": "2026-02-03T10:00:00",
                "ended_at": None,
                "risk_score": 15.5,
                "risk_level": "safe",
                "engagement_score": 92.0,
                "content_relevance": 88.0,
                "effort_alignment": 95.0,
                "status": "active",
                "stats": {
                    "tab_switches": 2,
                    "copy_events": 0,
                    "face_absences": 1,
                    "forbidden_sites": 0,
                    "total": 3
                }
            }
        }
