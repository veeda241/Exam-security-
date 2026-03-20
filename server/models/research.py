from typing import Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field
import uuid

class ResearchJourney(BaseModel):
    """Sequence of visited sites during a session (Supabase schema)"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    
    url: str
    title: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    dwell_time: int = 0  # Seconds spent on site
    
    # Categorization
    category: str = "General" # Documentation, Tutorial, Community, Search, Forbidden
    relevance_score: float = 0.5
    
    def to_dict(self):
        data = self.model_dump()
        if data["timestamp"] and hasattr(data["timestamp"], "isoformat"):
            data["timestamp"] = data["timestamp"].isoformat()
        return data

class SearchStrategy(BaseModel):
    """Aggregated insights about how the student researched (Supabase schema)"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    
    strategy_type: Optional[str] = None  # Documentation-first, Trial-and-error, etc.
    efficiency_score: float = 0.0 # 0-100
    source_diversity: float = 0.0
    
    insights: Optional[Any] = None
    
    def to_dict(self):
        return self.model_dump()
