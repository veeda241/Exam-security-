"""
ExamGuard Pro - Event Model
Database model for logged events
"""

from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from database import Base
import uuid


class Event(Base):
    """Logged event from extension"""
    __tablename__ = "events"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("exam_sessions.id"), nullable=False, index=True)
    
    # Event type
    event_type = Column(String, nullable=False, index=True)
    # Types: TAB_SWITCH, WINDOW_BLUR, COPY, PASTE, PAGE_HIDDEN, PAGE_VISIBLE,
    #        FORBIDDEN_SITE, FORBIDDEN_CONTENT, FACE_ABSENT, SUSPICIOUS_SHORTCUT,
    #        CONTEXT_MENU, SCREEN_SHARE_STOPPED
    
    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow)
    client_timestamp = Column(Integer, nullable=True)  # JS timestamp from client
    
    # Event data (JSON blob for flexibility)
    data = Column(JSON, nullable=True)
    
    # Risk weight applied
    risk_weight = Column(Integer, default=0)
    
    # Relationships
    session = relationship("ExamSession", back_populates="events")
    
    def to_dict(self):
        """Convert to dictionary for API response"""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "client_timestamp": self.client_timestamp,
            "data": self.data,
            "risk_weight": self.risk_weight,
        }
