from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
import uuid

class SessionStats(BaseModel):
    """Sub-model for session statistics"""
    tab_switches: int = 0
    copy_events: int = 0
    face_absences: int = 0
    forbidden_sites: int = 0
    phone_detections: int = 0
    total_events: int = 0

class ExamSession(BaseModel):
    """Exam session record (Supabase schema)"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    student_id: str
    student_name: str = "Unknown"
    exam_id: str
    
    # Timestamps
    started_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None
    
    # Status & Scoring
    is_active: bool = True
    status: str = "recording" # recording, processing, completed, flagged
    risk_score: float = 0.0
    risk_level: str = "safe"  # safe, review, suspicious
    
    # AI Analysis Scores (0-100)
    engagement_score: float = 100.0
    content_relevance: float = 100.0
    effort_alignment: float = 100.0
    
    # Stats
    tab_switch_count: int = 0
    copy_count: int = 0
    face_absence_count: int = 0
    forbidden_site_count: int = 0
    phone_detection_count: int = 0
    total_events: int = 0

    def to_dict(self):
        """Convert to dictionary for API response (matching legacy structure)"""
        data = self.model_dump()
        # Add legacy stats structure
        data["stats"] = {
            "tab_switches": self.tab_switch_count,
            "copy_events": self.copy_count,
            "face_absences": self.face_absence_count,
            "forbidden_sites": self.forbidden_site_count,
            "phone_detections": self.phone_detection_count,
            "total_events": self.total_events,
        }
        # Handle datetime serialization
        if data["started_at"]:
            data["started_at"] = data["started_at"].isoformat()
        if data["ended_at"]:
            data["ended_at"] = data["ended_at"].isoformat()
        return data
