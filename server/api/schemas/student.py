"""
ExamGuard Pro - Student Schemas
Pydantic models for student-related requests/responses
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class StudentCreate(BaseModel):
    """Schema for creating a new student"""
    id: Optional[str] = Field(None, description="Optional predetermined student ID (like a roll number)")
    name: str = Field(..., min_length=1, max_length=255, description="Student's full name")
    email: Optional[EmailStr] = Field(None, description="Student's email address")
    department: Optional[str] = Field(None, description="Department or Major")
    year: Optional[str] = Field(None, description="Year of study")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "CS1042",
                "name": "John Doe",
                "email": "john.doe@university.edu",
                "department": "Computer Science",
                "year": "Junior"
            }
        }


class StudentUpdate(BaseModel):
    """Schema for updating student information"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    department: Optional[str] = None
    year: Optional[str] = None


class StudentResponse(BaseModel):
    """Schema for student response"""
    id: str
    name: str
    email: Optional[str] = None
    department: Optional[str] = None
    year: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class StudentSummary(BaseModel):
    """Schema for student dashboard summary"""
    student_id: str
    name: str
    email: Optional[str] = None
    department: Optional[str] = None
    year: Optional[str] = None
    latest_session_id: Optional[str] = None
    risk_score: float = 0.0
    engagement_score: float = 0.0
    effort_alignment: float = 0.0
    content_relevance: float = 0.0
    tab_switch_count: int = 0
    forbidden_site_count: int = 0
    copy_count: int = 0
    status: str = "inactive"  # inactive, safe, review, suspicious
    
    class Config:
        json_schema_extra = {
            "example": {
                "student_id": "abc-123",
                "name": "John Doe",
                "email": "john@example.com",
                "department": "Computer Science",
                "year": "Junior",
                "latest_session_id": "sess-456",
                "risk_score": 25.5,
                "engagement_score": 85.0,
                "effort_alignment": 90.0,
                "status": "safe"
            }
        }
