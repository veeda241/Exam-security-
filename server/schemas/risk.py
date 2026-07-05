from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RiskConfigUpdate(BaseModel):
    weights: dict[str, float]
    thresholds: dict[str, float] = Field(default_factory=lambda: {"review": 30, "suspicious": 60})


class RiskConfigResponse(BaseModel):
    id: str
    version: int
    weights: dict[str, float]
    thresholds: dict[str, float]
    active: bool
