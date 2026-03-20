from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
import uuid

class Student(BaseModel):
    """Student record (Supabase schema)"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    email: Optional[str] = None
    department: Optional[str] = None
    year: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def to_dict(self):
        return self.model_dump()
