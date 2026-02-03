"""
ExamGuard Pro - Event Schemas
Pydantic models for event logging requests/responses
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class EventCreate(BaseModel):
    """Schema for creating a single event"""
    session_id: str = Field(..., description="Session identifier")
    event_type: str = Field(..., description="Type of event (tab_switch, copy, paste, etc.)")
    data: Dict[str, Any] = Field(default={}, description="Event-specific data")
    timestamp: Optional[int] = Field(None, description="Client-side JavaScript timestamp")


class EventData(BaseModel):
    """Schema for event data in batch operations"""
    type: str = Field(..., description="Event type")
    timestamp: int = Field(..., description="Client JS timestamp")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Event-specific data")
    id: Optional[str] = Field(default=None, description="Client-generated event ID")
    
    class Config:
        json_schema_extra = {
            "example": {
                "type": "tab_switch",
                "timestamp": 1706972400000,
                "data": {"from_tab": "exam", "to_tab": "other"},
                "id": "evt-123"
            }
        }


class EventBatch(BaseModel):
    """Schema for batch event submission"""
    session_id: str = Field(..., description="Session identifier")
    events: List[EventData] = Field(..., min_length=1, description="List of events to log")
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "session-123",
                "events": [
                    {"type": "tab_switch", "timestamp": 1706972400000, "data": {}},
                    {"type": "copy", "timestamp": 1706972401000, "data": {"text_length": 150}}
                ]
            }
        }


class EventResponse(BaseModel):
    """Schema for event creation response"""
    id: str
    session_id: str
    event_type: str
    timestamp: str
    risk_weight: int = 0

    class Config:
        from_attributes = True
