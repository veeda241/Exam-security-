"""
ExamGuard Pro - Analysis Result Model
Database model for AI analysis results
"""

from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Float, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from database import Base
import uuid


class AnalysisResult(Base):
    """AI analysis result record"""
    __tablename__ = "analysis_results"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("exam_sessions.id"), nullable=False, index=True)
    
    # Analysis type
    analysis_type = Column(String, nullable=False)
    # Types: FACE_DETECTION, OCR, TEXT_SIMILARITY, ANOMALY
    
    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Source reference (screenshot or webcam frame path)
    source_file = Column(String, nullable=True)
    
    # Results
    result_data = Column(JSON, nullable=True)
    
    # Face detection specific
    face_detected = Column(Boolean, nullable=True)
    face_confidence = Column(Float, nullable=True)
    
    # OCR specific
    detected_text = Column(String, nullable=True)
    forbidden_keywords_found = Column(JSON, nullable=True)
    
    # Similarity specific
    similarity_score = Column(Float, nullable=True)
    matched_content = Column(String, nullable=True)
    
    # Risk contribution
    risk_score_added = Column(Float, default=0.0)
    
    # Relationships
    session = relationship("ExamSession", back_populates="analysis_results")
    
    def to_dict(self):
        """Convert to dictionary for API response"""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "analysis_type": self.analysis_type,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "source_file": self.source_file,
            "result_data": self.result_data,
            "face_detected": self.face_detected,
            "face_confidence": self.face_confidence,
            "detected_text": self.detected_text[:200] if self.detected_text else None,
            "forbidden_keywords_found": self.forbidden_keywords_found,
            "similarity_score": self.similarity_score,
            "risk_score_added": self.risk_score_added,
        }
