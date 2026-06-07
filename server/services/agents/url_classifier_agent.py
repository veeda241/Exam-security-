"""Content/JS-signal page classifier agent for the v2 scoring pipeline."""

from __future__ import annotations

from typing import Any

from services.page_classifier import classify_page

from .base_agent import AgentBase, PageContext, Verdict

_TRACKER_TO_AGENT = {
    "exam": "exam_platform",
    "quiz": "exam_platform",
    "education": "educational",
    "learning": "educational",
    "ai": "ai",
    "cheating": "cheating",
    "entertainment": "entertainment",
    "social": "social",
    "other": "unknown",
}


class URLClassifierAgent(AgentBase):
    """Detects site type from page content, metadata, and DOM/JS signals — not domain lists."""

    name = "url_classifier"
    weight = 1.35

    async def analyze(self, context: PageContext) -> Verdict:
        signals: dict[str, Any] = {}
        if isinstance(context.extra, dict):
            nested = context.extra.get("signals")
            if isinstance(nested, dict):
                signals = dict(nested)
            page_ctx = context.extra.get("page_context")
            if isinstance(page_ctx, dict) and isinstance(page_ctx.get("signals"), dict):
                signals = {**signals, **page_ctx["signals"]}

        result = classify_page(
            url=context.url,
            title=context.title,
            content=context.content,
            signals=signals,
        )

        category = _TRACKER_TO_AGENT.get(result.tracker_category, "unknown")
        evidence = [
            f"content model: {result.tracker_category} ({result.method})",
            result.reason,
        ]

        if context.recent_domains:
            risky_recent = 0
            for recent_domain in context.recent_domains:
                recent_result = classify_page(url=f"https://{recent_domain}", title=recent_domain)
                if recent_result.tracker_category in {"ai", "cheating", "entertainment"}:
                    risky_recent += 1
            if risky_recent:
                penalty = min(10.0, risky_recent * 2.5)
                result.risk_score = min(100.0, result.risk_score + penalty)
                evidence.append(f"recent risky browsing context: {risky_recent}")

        return Verdict(
            agent_name=self.name,
            category=category,
            label=self._label_from_risk(result.risk_score),
            risk_score=self._clamp(result.risk_score),
            effort_score=self._clamp(result.effort_score),
            confidence=self._clamp(result.confidence, 0.0, 0.99),
            reason=", ".join(evidence),
            evidence=evidence,
            signals={
                "domain": context.domain,
                "path": context.path,
                "classification_method": result.method,
                "tracker_category": result.tracker_category,
                "content_scores": (result.signals or {}).get("content_scores", {}),
            },
            weight=self.weight,
        )
