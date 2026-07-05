from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


ML_EVENT_TYPES = frozenset({
    "frame_sample",
    "answer_submit",
    "screenshot",
})


CLIENT_EVENT_TYPES = frozenset({
    "tab_switch",
    "window_blur",
    "copy_paste",
    "page_hidden",
    "forbidden_site",
})


class EventCreate(BaseModel):
    session_id: str
    type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    ts: Optional[datetime] = None


class EventResponse(BaseModel):
    id: str
    session_id: str
    type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    weight: float = 0
    screenshot_url: Optional[str] = None
    created_at: Optional[datetime] = None


class EventIngestResponse(BaseModel):
    status: str = "accepted"
    event_id: Optional[str] = None
    job_id: Optional[str] = None
