"""
ExamGuard Pro - Event Model
SQLAlchemy model for proctoring events
"""

from sqlalchemy import Column, String, Integer, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from database import Base


def generate_uuid():
    return str(uuid.uuid4())


class Event(Base):
    """Event log model - tracks all proctoring events"""
    __tablename__ = "events"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    session_id = Column(String, ForeignKey("exam_sessions.id"), nullable=False)
    event_type = Column(String(50), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    client_timestamp = Column(Integer, nullable=True)  # JS timestamp from client
    data = Column(JSON, default={})
    risk_weight = Column(Integer, default=0)
    
    # Relationships
    session = relationship("ExamSession", back_populates="events")
    
    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "client_timestamp": self.client_timestamp,
            "data": self.data,
            "risk_weight": self.risk_weight
        }
    
    def __repr__(self):
        return f"<Event(id={self.id}, type={self.event_type}, session={self.session_id})>"
