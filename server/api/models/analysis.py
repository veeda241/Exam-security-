"""
ExamGuard Pro - Analysis Result Model
SQLAlchemy model for AI analysis results
"""

from sqlalchemy import Column, String, Float, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from database import Base


def generate_uuid():
    return str(uuid.uuid4())


class AnalysisResult(Base):
    """AI Analysis result model - stores results from various analysis engines"""
    __tablename__ = "analysis_results"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    session_id = Column(String, ForeignKey("exam_sessions.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    analysis_type = Column(String(50), nullable=False)  # FACE, OCR, SIMILARITY, ANOMALY, TRANSFORMER
    
    # Face Detection Results
    face_detected = Column(Boolean, default=True)
    face_confidence = Column(Float, default=0.0)
    
    # OCR Results
    detected_text = Column(Text, nullable=True)
    forbidden_keywords_found = Column(JSON, default=[])
    
    # Text Similarity Results
    similarity_score = Column(Float, default=0.0)
    
    # Risk Impact
    risk_score_added = Column(Float, default=0.0)
    
    # Full result data (JSON blob for flexibility)
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
            "face_confidence": self.face_confidence,
            "detected_text": self.detected_text,
            "forbidden_keywords_found": self.forbidden_keywords_found,
            "similarity_score": self.similarity_score,
            "risk_score_added": self.risk_score_added,
            "result_data": self.result_data,
            "source_file": self.source_file
        }
    
    def __repr__(self):
        return f"<AnalysisResult(id={self.id}, type={self.analysis_type}, session={self.session_id})>"
