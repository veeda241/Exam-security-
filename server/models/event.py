from typing import Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field
import uuid

class Event(BaseModel):
    """Logged event from extension (Supabase schema)"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    
    # Event type
    event_type: str
    
    # Timestamp
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    client_timestamp: Optional[int] = None  # JS timestamp from client
    
    # Event data (JSON blob for flexibility)
    data: Optional[Any] = None
    
    # Risk weight applied
    risk_weight: int = 0
    
    def to_dict(self):
        """Convert to dictionary for API response"""
        data = self.model_dump()
        if data["timestamp"] and hasattr(data["timestamp"], "isoformat"):
            data["timestamp"] = data["timestamp"].isoformat()
        return data
