"""
ExamGuard Pro - Research Models
SQLAlchemy models for research journey tracking
"""

from sqlalchemy import Column, String, Integer, Float, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from database import Base


def generate_uuid():
    return str(uuid.uuid4())


class ResearchJourney(Base):
    """Research journey model - tracks student browsing during exam"""
    __tablename__ = "research_journeys"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    session_id = Column(String, ForeignKey("exam_sessions.id"), nullable=False)
    
    # Page visited
    url = Column(String(2000), nullable=False)
    title = Column(String(500), nullable=True)
    domain = Column(String(255), nullable=True)
    
    # Timing
    timestamp = Column(DateTime, default=datetime.utcnow)
    dwell_time = Column(Integer, default=0)  # Time spent on page in seconds
    
    # Classification
    category = Column(String(50), nullable=True)  # search, reference, forbidden, etc.
    relevance_score = Column(Float, default=0.0)
    
    # Content analysis
    extracted_text = Column(Text, nullable=True)
    
    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "url": self.url,
            "title": self.title,
            "domain": self.domain,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "dwell_time": self.dwell_time,
            "category": self.category,
            "relevance_score": self.relevance_score
        }
    
    def __repr__(self):
        return f"<ResearchJourney(id={self.id}, url={self.url[:50]}...)>"


class SearchStrategy(Base):
    """Search strategy model - analysis of student's search patterns"""
    __tablename__ = "search_strategies"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    session_id = Column(String, ForeignKey("exam_sessions.id"), nullable=False)
    
    # Strategy metrics
    search_count = Column(Integer, default=0)
    unique_sources = Column(Integer, default=0)
    avg_dwell_time = Column(Float, default=0.0)
    depth_score = Column(Float, default=0.0)  # How deep they dig into topics
    breadth_score = Column(Float, default=0.0)  # How many different topics explored
    
    # Classification
    strategy_type = Column(String(50), nullable=True)  # surface, deep, focused, scattered
    effort_indicator = Column(Float, default=0.0)
    
    # Analysis timestamp
    analyzed_at = Column(DateTime, default=datetime.utcnow)
    
    # Full analysis data
    analysis_data = Column(JSON, default={})
    
    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "search_count": self.search_count,
            "unique_sources": self.unique_sources,
            "avg_dwell_time": self.avg_dwell_time,
            "depth_score": self.depth_score,
            "breadth_score": self.breadth_score,
            "strategy_type": self.strategy_type,
            "effort_indicator": self.effort_indicator,
            "analyzed_at": self.analyzed_at.isoformat() if self.analyzed_at else None
        }
    
    def __repr__(self):
        return f"<SearchStrategy(id={self.id}, type={self.strategy_type})>"
