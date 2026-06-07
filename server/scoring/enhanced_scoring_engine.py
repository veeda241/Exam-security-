"""Enhanced scoring engine for agent-based site analysis."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping

from services.agents import PageContext, SiteVerdict


@dataclass(slots=True)
class EnhancedScore:
    """Final scoring response returned by the v2 endpoint."""

    session_id: str = ""
    student_id: str = ""
    url: str = ""
    domain: str = ""
    path: str = ""
    site_category: str = "unknown"
    youtube_intent: str = "unknown"
    consensus: str = "safe"
    primary_agent: str = ""
    risk_score: float = 0.0
    effort_score: float = 100.0
    decay_factor: float = 1.0
    confidence: float = 0.0
    risk_level: str = "safe"
    recommended_action: str = "allow"
    summary: str = ""
    score_components: dict[str, Any] = field(default_factory=dict)
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
            "primary_agent": self.primary_agent,
            "risk_score": round(self.risk_score, 2),
            "effort_score": round(self.effort_score, 2),
            "decay_factor": round(self.decay_factor, 3),
            "confidence": round(self.confidence, 3),
            "risk_level": self.risk_level,
            "recommended_action": self.recommended_action,
            "summary": self.summary,
            "score_components": dict(self.score_components),
            "agent_details": dict(self.agent_details),
            "signals": dict(self.signals),
            "generated_at": self.generated_at.isoformat(),
        }


class EnhancedScoringEngine:
    """Combines agent consensus with signal-based decay and penalties."""

    name = "enhanced_scoring_engine"

    SAFE_THRESHOLD = 30.0
    REVIEW_THRESHOLD = 60.0
    DECAY_FLOOR = 0.60
    DECAY_WINDOW_SECONDS = 1_200.0

    TAB_SWITCH_PENALTY = 2.0
    COPY_PENALTY = 2.8
    PASTE_PENALTY = 1.4
    FOCUS_PENALTY = 1.8
    HIDDEN_PENALTY = 1.6

    CHEATING_BONUS = 12.0
    AI_BONUS = 6.0
    ENTERTAINMENT_BONUS = 8.0
    SOCIAL_BONUS = 6.0
    EDUCATIONAL_BONUS = 8.0
    YOUTUBE_EDU_BONUS = 8.0
    YOUTUBE_ENTERTAINMENT_BONUS = 10.0

    def enhance(self, context: PageContext, verdict: SiteVerdict) -> EnhancedScore:
        decay_factor = self._decay_factor(context)
        tab_switch_penalty = self._count_penalty(context.tab_switch_count, self.TAB_SWITCH_PENALTY)
        copy_penalty = self._count_penalty(context.copy_count, self.COPY_PENALTY)
        paste_penalty = self._count_penalty(context.paste_count, self.PASTE_PENALTY)
        focus_penalty = self._count_penalty(context.focus_lost_count, self.FOCUS_PENALTY)
        hidden_penalty = self._count_penalty(context.hidden_count, self.HIDDEN_PENALTY)

        base_risk = verdict.base_risk_score
        base_effort = verdict.base_effort_score
        category_adjustment = self._category_adjustment(verdict.site_category)
        youtube_adjustment = self._youtube_adjustment(verdict.youtube_intent)
        recent_domain_penalty = self._recent_domain_penalty(context)
        confidence_penalty = (1.0 - verdict.confidence) * 6.0

        signal_penalty = (
            tab_switch_penalty
            + copy_penalty
            + paste_penalty
            + focus_penalty
            + hidden_penalty
            + recent_domain_penalty
        )

        raw_risk = base_risk + signal_penalty + category_adjustment + youtube_adjustment + confidence_penalty
        risk_score = self._clamp(raw_risk * decay_factor)

        productivity_boost = self._productivity_boost(verdict.site_category, verdict.youtube_intent)
        raw_effort = base_effort - (signal_penalty * 0.55) + productivity_boost
        effort_score = self._clamp(raw_effort * (0.72 + (decay_factor * 0.28)))

        risk_level = self._risk_level(risk_score)
        recommended_action = self._recommended_action(risk_level)

        score_components = {
            "base_risk": round(base_risk, 2),
            "base_effort": round(base_effort, 2),
            "signal_penalty": round(signal_penalty, 2),
            "tab_switch_penalty": round(tab_switch_penalty, 2),
            "copy_penalty": round(copy_penalty, 2),
            "paste_penalty": round(paste_penalty, 2),
            "focus_penalty": round(focus_penalty, 2),
            "hidden_penalty": round(hidden_penalty, 2),
            "category_adjustment": round(category_adjustment, 2),
            "youtube_adjustment": round(youtube_adjustment, 2),
            "productivity_boost": round(productivity_boost, 2),
            "recent_domain_penalty": round(recent_domain_penalty, 2),
            "confidence_penalty": round(confidence_penalty, 2),
            "decay_factor": round(decay_factor, 3),
            "raw_risk": round(raw_risk, 2),
            "raw_effort": round(raw_effort, 2),
        }

        summary = verdict.summary
        if signal_penalty:
            summary = f"{summary} | signal_penalty={signal_penalty:.1f}"

        return EnhancedScore(
            session_id=context.session_id,
            student_id=context.student_id,
            url=context.url,
            domain=context.domain,
            path=context.path,
            site_category=verdict.site_category,
            youtube_intent=verdict.youtube_intent,
            consensus=verdict.consensus,
            primary_agent=verdict.primary_agent,
            risk_score=risk_score,
            effort_score=effort_score,
            decay_factor=decay_factor,
            confidence=verdict.confidence,
            risk_level=risk_level,
            recommended_action=recommended_action,
            summary=summary,
            score_components=score_components,
            agent_details=verdict.agent_details,
            signals=verdict.signals,
        )

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "safe_threshold": self.SAFE_THRESHOLD,
            "review_threshold": self.REVIEW_THRESHOLD,
            "decay_floor": self.DECAY_FLOOR,
            "decay_window_seconds": self.DECAY_WINDOW_SECONDS,
            "penalties": {
                "tab_switch": self.TAB_SWITCH_PENALTY,
                "copy": self.COPY_PENALTY,
                "paste": self.PASTE_PENALTY,
                "focus_lost": self.FOCUS_PENALTY,
                "hidden": self.HIDDEN_PENALTY,
            },
        }

    def _decay_factor(self, context: PageContext) -> float:
        duration = max(context.tab_duration_seconds, 0.0)
        if duration <= 0:
            return 1.0
        decay = 1.0 - min(duration, self.DECAY_WINDOW_SECONDS) / (self.DECAY_WINDOW_SECONDS * 2.0)
        return max(self.DECAY_FLOOR, decay)

    def _count_penalty(self, count: int, per_item: float) -> float:
        if count <= 0:
            return 0.0
        return min(count * per_item, 24.0)

    def _category_adjustment(self, category: str) -> float:
        category = (category or "unknown").lower()
        if category in {"cheating", "forbidden_content"}:
            return self.CHEATING_BONUS
        if category == "ai":
            return self.AI_BONUS
        if category in {"entertainment", "social"}:
            return self.ENTERTAINMENT_BONUS if category == "entertainment" else self.SOCIAL_BONUS
        if category in {"educational", "exam_platform"}:
            return -self.EDUCATIONAL_BONUS
        return 0.0

    def _youtube_adjustment(self, intent: str) -> float:
        intent = (intent or "unknown").lower()
        if intent == "educational":
            return -self.YOUTUBE_EDU_BONUS
        if intent == "entertainment":
            return self.YOUTUBE_ENTERTAINMENT_BONUS
        if intent == "mixed":
            return 3.0
        return 0.0

    def _productivity_boost(self, category: str, intent: str) -> float:
        boost = 0.0
        category = (category or "unknown").lower()
        if category in {"educational", "exam_platform"}:
            boost += 10.0
        if category == "unknown":
            boost += 2.0
        if (intent or "").lower() == "educational":
            boost += 4.0
        return boost

    def _recent_domain_penalty(self, context: PageContext) -> float:
        if not context.recent_domains:
            return 0.0
        current = context.domain.lower()
        count = sum(1 for domain in context.recent_domains if current and current in domain.lower())
        return min(8.0, count * 1.5)

    def _risk_level(self, risk_score: float) -> str:
        if risk_score < self.SAFE_THRESHOLD:
            return "safe"
        if risk_score < self.REVIEW_THRESHOLD:
            return "review"
        return "suspicious"

    @staticmethod
    def _recommended_action(risk_level: str) -> str:
        if risk_level == "suspicious":
            return "flag_session"
        if risk_level == "review":
            return "surface_warning"
        return "allow"

    @staticmethod
    def _clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
        return max(minimum, min(maximum, value))


_ENGINE: EnhancedScoringEngine | None = None


def get_enhanced_scoring_engine() -> EnhancedScoringEngine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = EnhancedScoringEngine()
    return _ENGINE
