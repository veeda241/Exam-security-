from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ReportResponse(BaseModel):
    id: str
    session_id: str
    storage_path: Optional[str] = None
    signed_url: Optional[str] = None
    generated_at: Optional[datetime] = None
    status: str = "pending"


class ReportTriggerResponse(BaseModel):
    status: str = "queued"
    job_id: Optional[str] = None
