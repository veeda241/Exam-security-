"""NLP keyword and similarity agent for page content analysis."""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any
import re

from config import FORBIDDEN_KEYWORDS

from .base_agent import AgentBase, PageContext, Verdict


_STUDY_HINTS = (
    "lecture",
    "tutorial",
    "class",
    "course",
    "lesson",
    "practice",
    "example",
    "notes",
    "review",
    "revision",
    "study",
    "documentation",
    "walkthrough",
)

_ANSWER_HINTS = (
    "answer key",
    "final answer",
    "answers only",
    "step by step",
    "worked solution",
    "full solution",
    "chegg",
    "course hero",
    "quizlet",
    "brainly",
    "copy and paste",
    "copy paste",
    "generate answer",
    "write an essay",
)


class ContentAnalyzerAgent(AgentBase):
    """Flags forbidden content, copied answers, and low-effort text patterns."""

    name = "content_analyzer"
    weight = 1.2

    async def analyze(self, context: PageContext) -> Verdict:
        text = context.normalized_text
        if not text:
            return Verdict(
                agent_name=self.name,
                category="neutral",
                label="safe",
                risk_score=0.0,
                effort_score=100.0,
                confidence=0.18,
                reason="no page text available",
                evidence=["empty content payload"],
                signals={"forbidden_keywords": [], "study_keywords": [], "clipboard_similarity": 0.0},
                weight=self.weight,
            )

        forbidden_hits = self._matches_any(text, FORBIDDEN_KEYWORDS)
        study_hits = self._matches_any(text, _STUDY_HINTS)
        answer_hits = self._matches_any(text, _ANSWER_HINTS)
        clipboard_similarity = self._similarity(context.clipboard_text, context.content)
        subject_overlap = self._token_overlap(context.exam_subject, text)

        evidence: list[str] = []
        signals: dict[str, Any] = {
            "forbidden_keywords": forbidden_hits,
            "study_keywords": study_hits,
            "answer_keywords": answer_hits,
            "clipboard_similarity": round(clipboard_similarity, 3),
            "subject_overlap": round(subject_overlap, 3),
        }

        risk_score = 8.0
        effort_score = 92.0
        confidence = 0.35

        if forbidden_hits:
            risk_score += min(40.0, len(forbidden_hits) * 7.5)
            evidence.append(f"forbidden keywords: {', '.join(forbidden_hits[:4])}")
            confidence += 0.22

        if answer_hits:
            risk_score += min(24.0, len(answer_hits) * 6.0)
            evidence.append(f"answer-like phrasing: {', '.join(answer_hits[:4])}")
            confidence += 0.18

        if context.clipboard_text and clipboard_similarity >= 0.82:
            risk_score += 18.0
            effort_score -= 14.0
            evidence.append(f"clipboard/page similarity {clipboard_similarity:.2f}")
            confidence += 0.12

        if subject_overlap >= 0.35 and study_hits:
            risk_score = max(0.0, risk_score - 8.0)
            effort_score = min(100.0, effort_score + 8.0)
            evidence.append("subject aligned with study content")

        if study_hits:
            effort_score = min(100.0, effort_score + min(10.0, len(study_hits) * 2.0))
            confidence += 0.04

        if len(text) > 250 and not forbidden_hits and not answer_hits:
            risk_score = max(0.0, risk_score - 3.0)
            effort_score = min(100.0, effort_score + 2.0)

        category = "forbidden_content" if (forbidden_hits or answer_hits) else "study_support" if study_hits else "neutral"
        if risk_score >= 70.0:
            label = "suspicious"
        elif risk_score >= 30.0:
            label = "review"
        else:
            label = "safe"

        if not evidence:
            evidence.append("no strong content keyword signal")

        return Verdict(
            agent_name=self.name,
            category=category,
            label=label,
            risk_score=self._clamp(risk_score),
            effort_score=self._clamp(effort_score),
            confidence=self._clamp(confidence, 0.0, 0.99),
            reason=", ".join(evidence),
            evidence=evidence,
            signals=signals,
            weight=self.weight,
        )

    @staticmethod
    def _similarity(left: str, right: str) -> float:
        left_text = re.sub(r"\s+", " ", (left or "").strip().lower())
        right_text = re.sub(r"\s+", " ", (right or "").strip().lower())
        if not left_text or not right_text:
            return 0.0
        return SequenceMatcher(None, left_text, right_text).ratio()
