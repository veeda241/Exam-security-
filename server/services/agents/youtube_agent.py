"""YouTube intent classifier agent."""

from __future__ import annotations

from typing import Any

from .base_agent import AgentBase, PageContext, Verdict


_STUDY_HINTS = (
    "lecture",
    "tutorial",
    "class",
    "course",
    "lesson",
    "study",
    "review",
    "practice",
    "exam prep",
    "walkthrough",
    "how to",
    "explainer",
)

_ENTERTAINMENT_HINTS = (
    "music",
    "song",
    "live",
    "gaming",
    "funny",
    "comedy",
    "reaction",
    "podcast",
    "vlog",
    "shorts",
    "highlight",
)


class YouTubeAgent(AgentBase):
    """Classifies video intent and downgrades educational content."""

    name = "youtube_agent"
    weight = 1.0

    async def analyze(self, context: PageContext) -> Verdict:
        domain = context.domain.lower()
        combined = f"{context.url} {context.title} {context.youtube_title} {context.youtube_channel} {context.content}".lower()

        if "youtube" not in domain and "youtu.be" not in domain:
            return Verdict(
                agent_name=self.name,
                category="not_youtube",
                label="safe",
                risk_score=0.0,
                effort_score=100.0,
                confidence=0.12,
                reason="page is not a YouTube property",
                evidence=["non-youtube domain"],
                signals={"youtube_intent": "not_youtube", "is_youtube": False},
                weight=self.weight,
            )

        study_hits = self._matches_any(combined, _STUDY_HINTS)
        entertainment_hits = self._matches_any(combined, _ENTERTAINMENT_HINTS)
        path = context.path.lower()

        evidence: list[str] = []
        signals: dict[str, Any] = {
            "is_youtube": True,
            "path": path,
            "study_hits": study_hits,
            "entertainment_hits": entertainment_hits,
        }

        if study_hits and not entertainment_hits:
            intent = "educational"
            risk_score = 14.0
            effort_score = 95.0
            confidence = 0.86
            evidence.append(f"study cues: {', '.join(study_hits[:4])}")
        elif entertainment_hits and not study_hits:
            intent = "entertainment"
            risk_score = 70.0
            effort_score = 24.0
            confidence = 0.89
            evidence.append(f"entertainment cues: {', '.join(entertainment_hits[:4])}")
        else:
            intent = "mixed"
            risk_score = 42.0
            effort_score = 55.0
            confidence = 0.68
            if study_hits:
                evidence.append(f"mixed study cues: {', '.join(study_hits[:3])}")
            if entertainment_hits:
                evidence.append(f"mixed entertainment cues: {', '.join(entertainment_hits[:3])}")

        if "/shorts" in path:
            risk_score += 10.0
            effort_score -= 8.0
            evidence.append("shorts path detected")

        if "/watch" in path:
            evidence.append("watch path detected")

        if context.exam_subject and context.exam_subject.lower() in combined:
            risk_score = max(0.0, risk_score - 8.0)
            effort_score = min(100.0, effort_score + 6.0)
            evidence.append("exam subject appears in video metadata")

        if context.youtube_title and context.youtube_channel:
            signals["title"] = context.youtube_title
            signals["channel"] = context.youtube_channel

        return Verdict(
            agent_name=self.name,
            category=intent,
            label=self._label_from_risk(risk_score),
            risk_score=self._clamp(risk_score),
            effort_score=self._clamp(effort_score),
            confidence=self._clamp(confidence, 0.0, 0.99),
            reason=", ".join(evidence) if evidence else "youtube intent inferred from page metadata",
            evidence=evidence or ["youtube domain detected"],
            signals=signals,
            weight=self.weight,
        )
