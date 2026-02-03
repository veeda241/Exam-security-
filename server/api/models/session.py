"""
ExamGuard Pro - Exam Session Model
SQLAlchemy model for exam sessions
"""

from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from database import Base


def generate_uuid():
    return str(uuid.uuid4())


class ExamSession(Base):
    """Exam session model - represents a single exam attempt"""
    __tablename__ = "exam_sessions"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    student_id = Column(String, ForeignKey("students.id"), nullable=True)
    student_name = Column(String(255), nullable=False)
    exam_id = Column(String(100), nullable=False)
    
    # Timestamps
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Risk Scores
    risk_score = Column(Float, default=0.0)
    risk_level = Column(String(20), default="safe")  # safe, review, suspicious
    
    # AI Analysis Scores
    engagement_score = Column(Float, default=100.0)
    content_relevance = Column(Float, default=100.0)
    effort_alignment = Column(Float, default=100.0)
    
    # Event Counts
    tab_switch_count = Column(Integer, default=0)
    copy_count = Column(Integer, default=0)
    face_absence_count = Column(Integer, default=0)
    forbidden_site_count = Column(Integer, default=0)
    total_events = Column(Integer, default=0)
    
    # Relationships
    student = relationship("Student", back_populates="sessions")
    events = relationship("Event", back_populates="session", cascade="all, delete-orphan")
    analysis_results = relationship("AnalysisResult", back_populates="session", cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            "id": self.id,
            "student_id": self.student_id,
            "student_name": self.student_name,
            "exam_id": self.exam_id,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "status": "active" if self.is_active else "ended",
            "risk_score": self.risk_score,
            "risk_level": self.risk_level,
            "engagement_score": self.engagement_score,
            "content_relevance": self.content_relevance,
            "effort_alignment": self.effort_alignment,
            "stats": {
                "tab_switches": self.tab_switch_count,
                "copy_events": self.copy_count,
                "face_absences": self.face_absence_count,
                "forbidden_sites": self.forbidden_site_count,
                "total": self.total_events
            }
        }
    
    def __repr__(self):
        return f"<ExamSession(id={self.id}, student={self.student_name}, exam={self.exam_id})>"
