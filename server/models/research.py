from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Float, JSON
from sqlalchemy.orm import relationship
from database import Base
import uuid

class ResearchJourney(Base):
    """Sequence of visited sites during a session"""
    __tablename__ = "research_journey"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("exam_sessions.id"), nullable=False, index=True)
    
    url = Column(String, nullable=False)
    title = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    dwell_time = Column(Integer, default=0)  # Seconds spent on site
    
    # Categorization
    category = Column(String, default="General") # Documentation, Tutorial, Community, Search, Forbidden
    relevance_score = Column(Float, default=0.5)
    
    # Relationships
    session = relationship("ExamSession")

class SearchStrategy(Base):
    """Aggregated insights about how the student researched"""
    __tablename__ = "search_strategies"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("exam_sessions.id"), nullable=False, index=True, unique=True)
    
    strategy_type = Column(String)  # Documentation-first, Trial-and-error, etc.
    efficiency_score = Column(Float, default=0.0) # 0-100
    source_diversity = Column(Float, default=0.0)
    
    insights = Column(JSON, nullable=True)
    
    # Relationships
    session = relationship("ExamSession")
