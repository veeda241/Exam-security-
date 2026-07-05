from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class ConsentMetadata(BaseModel):
    consented_at: Optional[datetime] = None
    retention_mode: str = "standard"
    biometric_consent: bool = True
    monitoring_tier: str = "full"
    policy_version: int = 1


class SessionCreate(BaseModel):
    exam_id: str
    consent_metadata: ConsentMetadata = Field(default_factory=ConsentMetadata)


class SessionUpdate(BaseModel):
    status: Optional[str] = None
    ended_at: Optional[datetime] = None


class SessionResponse(BaseModel):
    id: str
    exam_id: str
    student_id: Optional[str] = None
    status: str
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    risk_score: float = 0
    risk_level: str = "safe"
    consent_metadata: dict[str, Any] = Field(default_factory=dict)
    monitoring_tier: str = "full"
    created_at: Optional[datetime] = None
