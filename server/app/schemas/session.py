from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class SessionBase(BaseModel):
    student_id: str
    exam_id: str

class SessionCreate(SessionBase):
    pass

class SessionResponse(SessionBase):
    id: str
    status: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    risk_score: float = 0.0

    class Config:
        from_attributes = True
