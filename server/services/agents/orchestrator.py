"""Consensus orchestrator for the v2 agent scoring pipeline."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Sequence
import asyncio

from .base_agent import AgentBase, PageContext, Verdict
from .content_analyzer_agent import ContentAnalyzerAgent
from .url_classifier_agent import URLClassifierAgent
from .youtube_agent import YouTubeAgent


@dataclass(slots=True)
class SiteVerdict:
    """Aggregated consensus verdict produced by the agent orchestrator."""

    session_id: str = ""
    student_id: str = ""
    url: str = ""
    domain: str = ""
    path: str = ""
    site_category: str = "unknown"
    youtube_intent: str = "unknown"
    consensus: str = "safe"
    base_risk_score: float = 0.0
    base_effort_score: float = 100.0
    confidence: float = 0.0
    primary_agent: str = ""
    recommended_action: str = "allow"
    summary: str = ""
    agent_details: dict[str, dict[str, Any]] = field(default_factory=dict)
    signals: dict[str, Any] = field(default_factory=dict)
    generated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "student_id": self.student_id,
            "url": self.url,
            "domain": self.domain,
            "path": self.path,
            "site_category": self.site_category,
            "youtube_intent": self.youtube_intent,
            "consensus": self.consensus,
            "base_risk_score": round(self.base_risk_score, 2),
            "base_effort_score": round(self.base_effort_score, 2),
            "confidence": round(self.confidence, 3),
            "primary_agent": self.primary_agent,
            "recommended_action": self.recommended_action,
            "summary": self.summary,
            "agent_details": dict(self.agent_details),
            "signals": dict(self.signals),
            "generated_at": self.generated_at.isoformat(),
        }


class ScoringOrchestrator:
    """Runs the site agents and derives a consensus verdict."""

    def __init__(self, agents: Sequence[AgentBase] | None = None):
        self.agents: tuple[AgentBase, ...] = tuple(
            agents
            if agents is not None
            else (
                URLClassifierAgent(),
                ContentAnalyzerAgent(),
                YouTubeAgent(),
            )
        )

    async def analyze(self, context: PageContext) -> SiteVerdict:
        if not self.agents:
            return SiteVerdict(
                session_id=context.session_id,
                student_id=context.student_id,
                url=context.url,
                domain=context.domain,
                path=context.path,
                summary="No scoring agents registered",
            )

        verdicts = await asyncio.gather(*(agent.analyze(context) for agent in self.agents))
        return self._build_site_verdict(context, verdicts)

    def describe_agents(self) -> list[dict[str, Any]]:
        return [
            {
                "name": agent.name,
                "weight": agent.weight,
                "module": agent.__class__.__module__,
                "description": agent.__doc__.strip() if agent.__doc__ else "",
            }
            for agent in self.agents
        ]

    def _build_site_verdict(self, context: PageContext, verdicts: Sequence[Verdict]) -> SiteVerdict:
        if not verdicts:
            return SiteVerdict(
                session_id=context.session_id,
                student_id=context.student_id,
                url=context.url,
                domain=context.domain,
                path=context.path,
                summary="No agent verdicts returned",
            )

        total_weight = sum(max(verdict.weight, 0.1) for verdict in verdicts) or 1.0
        weighted_risk = sum(verdict.risk_score * verdict.weight for verdict in verdicts) / total_weight
        weighted_effort = sum(verdict.effort_score * verdict.weight for verdict in verdicts) / total_weight
        weighted_confidence = sum(verdict.confidence * verdict.weight for verdict in verdicts) / total_weight

        label_counts = Counter(verdict.label for verdict in verdicts)
        severity_rank = {"safe": 0, "review": 1, "suspicious": 2}
        dominant = max(verdicts, key=lambda verdict: (verdict.risk_score, verdict.confidence, verdict.weight))
        consensus = self._consensus_label(weighted_risk, label_counts)

        youtube_verdict = next((verdict for verdict in verdicts if verdict.agent_name == "youtube_agent"), None)
        youtube_intent = youtube_verdict.category if youtube_verdict else "unknown"
        primary_agent = dominant.agent_name
        site_category = dominant.category

        confidence = self._clamp(
            (weighted_confidence * 0.7)
            + (max(label_counts.values()) / max(len(verdicts), 1)) * 0.3,
            0.0,
            0.99,
        )

        if consensus == "suspicious":
            recommended_action = "flag_session"
        elif consensus == "review":
            recommended_action = "surface_warning"
        else:
            recommended_action = "allow"

        summary_parts = [
            f"{context.domain or context.url or 'unknown'} -> {consensus} ({weighted_risk:.1f}/100)",
            f"primary={primary_agent}",
        ]
        if youtube_intent and youtube_intent not in {"unknown", "not_youtube"}:
            summary_parts.append(f"youtube_intent={youtube_intent}")
        if dominant.reason:
            summary_parts.append(dominant.reason)

        agent_details = {verdict.agent_name: verdict.to_dict() for verdict in verdicts}
        signals = self._aggregate_signals(verdicts)

        return SiteVerdict(
            session_id=context.session_id,
            student_id=context.student_id,
            url=context.url,
            domain=context.domain,
            path=context.path,
            site_category=site_category,
            youtube_intent=youtube_intent,
            consensus=consensus,
            base_risk_score=self._clamp(weighted_risk, 0.0, 100.0),
            base_effort_score=self._clamp(weighted_effort, 0.0, 100.0),
            confidence=confidence,
            primary_agent=primary_agent,
            recommended_action=recommended_action,
            summary=" | ".join(summary_parts),
            agent_details=agent_details,
            signals=signals,
        )

    @staticmethod
    def _consensus_label(weighted_risk: float, label_counts: Counter[str]) -> str:
        suspicious_votes = label_counts.get("suspicious", 0)
        review_votes = label_counts.get("review", 0)

        if weighted_risk >= 70.0 or suspicious_votes >= 2:
            return "suspicious"
        if weighted_risk >= 30.0 or review_votes >= 1 or suspicious_votes == 1:
            return "review"
        return "safe"

    @staticmethod
    def _aggregate_signals(verdicts: Sequence[Verdict]) -> dict[str, Any]:
        aggregated: dict[str, Any] = {
            "agent_labels": {},
            "agent_categories": {},
            "evidence": [],
            "matched_sites": [],
            "forbidden_keywords": [],
            "study_keywords": [],
            "answer_keywords": [],
            "youtube_intent": "unknown",
        }

        for verdict in verdicts:
            aggregated["agent_labels"][verdict.agent_name] = verdict.label
            aggregated["agent_categories"][verdict.agent_name] = verdict.category
            aggregated["evidence"].extend(verdict.evidence)

            for key, value in verdict.signals.items():
                if key == "youtube_intent" and value not in {None, "", "unknown", "not_youtube"}:
                    aggregated["youtube_intent"] = value
                elif isinstance(value, list):
                    bucket = aggregated.setdefault(key, [])
                    for item in value:
                        if item not in bucket:
                            bucket.append(item)
                elif key not in aggregated or aggregated[key] in {None, "", "unknown"}:
                    aggregated[key] = value

        aggregated["evidence"] = list(dict.fromkeys(aggregated["evidence"]))
        return aggregated

    @staticmethod
    def _clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
        return max(minimum, min(maximum, value))


_ORCHESTRATOR: ScoringOrchestrator | None = None


def get_site_orchestrator() -> ScoringOrchestrator:
    global _ORCHESTRATOR
    if _ORCHESTRATOR is None:
        _ORCHESTRATOR = ScoringOrchestrator()
    return _ORCHESTRATOR
