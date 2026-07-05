from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class RetentionPolicy(BaseModel):
    mode: str = "standard"
    screenshot_days: int = 30
    extended_screenshot_days: int = 90
    derived_events_days: int = 365


class ExamRuleset(BaseModel):
    allowed_tabs: list[str] = Field(default_factory=list)
    allow_copy_paste: bool = False
    webcam_interval_seconds: int = 5
    screenshot_interval_seconds: int = 5
    retention: RetentionPolicy = Field(default_factory=RetentionPolicy)
    biometric_monitoring: str = "required"
    alternative_mode: str = "reduced_monitoring"


class ExamCreate(BaseModel):
    title: str
    starts_at: Optional[datetime] = None
    duration_minutes: Optional[int] = 60
    ruleset: ExamRuleset = Field(default_factory=ExamRuleset)


class ExamUpdate(BaseModel):
    title: Optional[str] = None
    starts_at: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    ruleset: Optional[ExamRuleset] = None


class ExamResponse(BaseModel):
    id: str
    title: str
    created_by: Optional[str] = None
    starts_at: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    ruleset: dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
