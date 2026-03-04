"""
ExamGuard Pro - Session Model
Database model for exam sessions
"""

from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Boolean, Float, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
import uuid


class ExamSession(Base):
    """Exam session record"""
    __tablename__ = "exam_sessions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = Column(String, ForeignKey("students.id"), nullable=False, index=True)
    # student_name is available via relationship
    
    exam_id = Column(String, nullable=False, index=True)
    
    # Timestamps
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Risk score (calculated)
    risk_score = Column(Float, default=0.0)
    risk_level = Column(String, default="safe")  # safe, review, suspicious
    
    # AI Analysis Scores (0-100)
    engagement_score = Column(Float, default=100.0)
    content_relevance = Column(Float, default=100.0)
    effort_alignment = Column(Float, default=100.0)
    
    # Status
    status = Column(String, default="recording") # recording, processing, completed, flagged
    
    # Stats
    tab_switch_count = Column(Integer, default=0)
    copy_count = Column(Integer, default=0)
    face_absence_count = Column(Integer, default=0)
    forbidden_site_count = Column(Integer, default=0)
    total_events = Column(Integer, default=0)
    
    # Relationships
    student = relationship("Student", back_populates="sessions")
    events = relationship("Event", back_populates="session", lazy="dynamic")
    analysis_results = relationship("AnalysisResult", back_populates="session", lazy="dynamic")
    
    def to_dict(self):
        """Convert to dictionary for API response"""
        student_name = self.student.name if self.student else "Unknown"
        return {
            "id": self.id,
            "student_id": self.student_id,
            "student_name": student_name,
            "exam_id": self.exam_id,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "is_active": self.is_active,
            "risk_score": self.risk_score,
            "risk_level": self.risk_level,
            "engagement_score": self.engagement_score,
            "content_relevance": self.content_relevance,
            "effort_alignment": self.effort_alignment,
            "status": self.status,
            "stats": {
                "tab_switches": self.tab_switch_count,
                "copy_events": self.copy_count,
                "face_absences": self.face_absence_count,
                "forbidden_sites": self.forbidden_site_count,
                "total_events": self.total_events,
            },
        }
