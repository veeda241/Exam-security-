"""v2 agent scoring endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from services.agents import PageContext, get_site_orchestrator
from scoring.enhanced_scoring_engine import get_enhanced_scoring_engine

router = APIRouter()


class AnalyzeSiteRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    session_id: Optional[str] = None
    student_id: Optional[str] = None
    url: str
    domain: Optional[str] = None
    path: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None
    clipboard_text: Optional[str] = None
    youtube_title: Optional[str] = None
    youtube_channel: Optional[str] = None
    exam_subject: Optional[str] = None
    referrer: Optional[str] = None
    tab_duration_seconds: float = 0.0
    tab_switch_count: int = 0
    copy_count: int = 0
    paste_count: int = 0
    focus_lost_count: int = 0
    hidden_count: int = 0
    recent_domains: List[str] = Field(default_factory=list)
    page_context: Dict[str, Any] = Field(default_factory=dict)
    signals: Dict[str, Any] = Field(default_factory=dict)


class SiteAnalysisResponse(BaseModel):
    status: str = "ok"
    session_id: Optional[str] = None
    student_id: Optional[str] = None
    url: str
    domain: str
    path: str
    site_category: str
    youtube_intent: str
    consensus: str
    primary_agent: str
    risk_score: float
    effort_score: float
    decay_factor: float
    confidence: float
    risk_level: str
    recommended_action: str
    summary: str
    score_components: Dict[str, Any]
    agent_details: Dict[str, Any]
    signals: Dict[str, Any]
    generated_at: datetime


class AgentSystemStatus(BaseModel):
    status: str = "ready"
    orchestrator: str
    agents: List[Dict[str, Any]]
    scoring_engine: Dict[str, Any]


@router.post("/analyze-site", response_model=SiteAnalysisResponse)
async def analyze_site(request: AnalyzeSiteRequest):
    if not request.url:
        raise HTTPException(status_code=400, detail="url is required")

    payload = request.model_dump(exclude_none=True)
    context = PageContext.from_mapping(payload)

    orchestrator = get_site_orchestrator()
    site_verdict = await orchestrator.analyze(context)

    engine = get_enhanced_scoring_engine()
    enhanced = engine.enhance(context, site_verdict)
    return enhanced.to_dict()


@router.get("/status", response_model=AgentSystemStatus)
async def agent_system_status():
    orchestrator = get_site_orchestrator()
    engine = get_enhanced_scoring_engine()
    return {
        "status": "ready",
        "orchestrator": orchestrator.__class__.__name__,
        "agents": orchestrator.describe_agents(),
        "scoring_engine": engine.describe(),
    }
