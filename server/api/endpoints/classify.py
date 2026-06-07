"""Fast page classification API for the extension."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from services.page_classifier import classify_for_tracker, classify_page

router = APIRouter()


class ClassifyPageRequest(BaseModel):
    url: str
    title: str = ""
    content: str = ""
    signals: Dict[str, Any] = Field(default_factory=dict)


class ClassifyPageResponse(BaseModel):
    category: str
    tracker_category: str
    site: str
    risk_level: str
    risk_score: float
    effort_score: float
    confidence: float
    method: str
    reason: str


@router.post("/page", response_model=ClassifyPageResponse)
async def classify_page_endpoint(request: ClassifyPageRequest):
    """Classify a page from URL + visible content + DOM/JS signals (no domain lists)."""
    result = classify_for_tracker(
        request.url,
        request.title,
        request.content,
        request.signals,
    )
    return ClassifyPageResponse(
        category=result["category"],
        tracker_category=result["trackerCategory"],
        site=result["site"],
        risk_level=result["riskLevel"],
        risk_score=result["riskScore"],
        effort_score=result["effortScore"],
        confidence=result["confidence"],
        method=result["method"],
        reason=result["reason"],
    )


@router.post("/page/detail")
async def classify_page_detail(request: ClassifyPageRequest):
    """Full classification payload including signal breakdown."""
    detail = classify_page(
        request.url,
        request.title,
        request.content,
        request.signals,
    )
    return {
        "category": detail.category,
        "tracker_category": detail.tracker_category,
        "risk_level": detail.risk_level,
        "risk_score": detail.risk_score,
        "effort_score": detail.effort_score,
        "confidence": detail.confidence,
        "method": detail.method,
        "reason": detail.reason,
        "signals": detail.signals,
    }
