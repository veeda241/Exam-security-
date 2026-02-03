"""
ExamGuard Pro - Report Schemas
Pydantic models for report generation requests/responses
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class ReportRequest(BaseModel):
    """Schema for report generation request"""
    session_id: str = Field(..., description="Session identifier")
    include_events: bool = Field(True, description="Include detailed event log")
    include_analysis: bool = Field(True, description="Include AI analysis results")
    include_screenshots: bool = Field(False, description="Include screenshot references")
    include_timeline: bool = Field(True, description="Include event timeline")
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "session-123",
                "include_events": True,
                "include_analysis": True,
                "include_screenshots": False,
                "include_timeline": True
            }
        }


class ReportSummary(BaseModel):
    """Schema for report summary"""
    session_id: str
    student_name: str
    exam_id: str
    duration_seconds: float
    risk_score: float
    risk_level: str
    event_counts: Dict[str, int] = {}
    high_risk_events: List[Dict[str, Any]] = []
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "session-123",
                "student_name": "John Doe",
                "exam_id": "midterm-2026",
                "duration_seconds": 3600.0,
                "risk_score": 25.5,
                "risk_level": "safe",
                "event_counts": {
                    "tab_switches": 5,
                    "copy_events": 2,
                    "face_absences": 1,
                    "forbidden_sites": 0,
                    "total": 8
                },
                "high_risk_events": []
            }
        }


class ReportResponse(BaseModel):
    """Schema for full report response"""
    report: Dict[str, Any]
    generated_at: str
    format: str = "json"  # json, pdf
    download_url: Optional[str] = None


class ReportEventItem(BaseModel):
    """Schema for individual event in report"""
    id: str
    event_type: str
    timestamp: str
    risk_weight: int
    data: Dict[str, Any] = {}


class ReportAnalysisItem(BaseModel):
    """Schema for individual analysis result in report"""
    id: str
    analysis_type: str
    timestamp: str
    face_detected: Optional[bool] = None
    similarity_score: Optional[float] = None
    risk_score_added: float = 0.0
