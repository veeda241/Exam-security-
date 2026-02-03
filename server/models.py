"""
ExamGuard Pro - Consolidated Database Models
SQLAlchemy models for PostgreSQL
"""

from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from database import Base


def generate_uuid():
    return str(uuid.uuid4())


class Student(Base):
    """Student model"""
    __tablename__ = "students"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    sessions = relationship("ExamSession", back_populates="student")
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class ExamSession(Base):
    """Exam session model"""
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


class Event(Base):
    """Event log model"""
    __tablename__ = "events"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    session_id = Column(String, ForeignKey("exam_sessions.id"), nullable=False)
    event_type = Column(String(50), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    data = Column(JSON, default={})
    
    # Relationships
    session = relationship("ExamSession", back_populates="events")
    
    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "data": self.data
        }


class AnalysisResult(Base):
    """AI Analysis result model"""
    __tablename__ = "analysis_results"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    session_id = Column(String, ForeignKey("exam_sessions.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    analysis_type = Column(String(50), nullable=False)  # FACE, OCR, SIMILARITY, ANOMALY
    
    # Face Detection
    face_detected = Column(Boolean, default=True)
    face_confidence = Column(Float, default=0.0)
    
    # OCR Results
    detected_text = Column(Text, nullable=True)
    forbidden_keywords_found = Column(JSON, default=[])
    
    # Text Similarity
    similarity_score = Column(Float, default=0.0)
    
    # Risk Impact
    risk_score_added = Column(Float, default=0.0)
    
    # Full result data
    result_data = Column(JSON, default={})
    source_file = Column(String(500), nullable=True)
    
    # Relationships
    session = relationship("ExamSession", back_populates="analysis_results")
    
    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "analysis_type": self.analysis_type,
            "face_detected": self.face_detected,
            "similarity_score": self.similarity_score,
            "risk_score_added": self.risk_score_added,
            "result_data": self.result_data
        }
