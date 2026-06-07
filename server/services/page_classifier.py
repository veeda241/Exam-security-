"""
Dynamic page classifier — uses page text, metadata, and DOM/JS signals.
No static domain allowlists; scales to any website via content + optional ML model.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import parse_qs, urlparse

# Keyword families scored against combined page context (title + body + meta)
_CATEGORY_PATTERNS: dict[str, dict[str, float]] = {
    "exam": {
        r"\b(proctor|proctoring|lockdown|exam portal|submit exam|final submit|time remaining)\b": 3.0,
        r"\b(honor code|respondus|examsoft|gradescope|mettl assessment)\b": 2.5,
        r"\b(examguard|proctor dashboard|live student feeds)\b": 2.5,
    },
    "quiz": {
        r"\b(kahoot|quizizz|quizlet live|socrative|nearpod|formative assessment)\b": 3.2,
        r"\b(start quiz|begin quiz|quiz timer|question \d+ of \d+|next question|submit quiz)\b": 2.8,
        r"\b(multiple choice|true or false|select the correct answer|quiz attempt)\b": 2.5,
        r"\b(practice quiz|chapter quiz|unit test|mock test|sample questions)\b": 2.2,
    },
    "education": {
        r"\b(my courses|course dashboard|enrolled courses|learning path|course catalog)\b": 2.8,
        r"\b(lesson module|module progress|watch lecture|course content|study material)\b": 2.5,
        r"\b(khan academy|coursera|udemy|edx|codecademy|skillshare|pluralsight|datacamp)\b": 2.6,
        r"\b(google classroom|canvas lms|moodle|blackboard|schoology|brightspace)\b": 2.8,
        r"\b(tutorial|documentation|course module|lecture notes|study guide|lesson plan)\b": 2.0,
    },
    "learning": {
        r"\b(stack overflow|github|stackoverflow|api reference|getting started|walkthrough)\b": 1.8,
        r"\b(wikipedia|research paper|arxiv|textbook|syllabus|assignment instructions)\b": 1.5,
        r"\b(code editor|programming exercise|leetcode|hackerrank|coding challenge)\b": 1.8,
        r"\b(exam preparation|study for exam|practice test|review questions|lecture notes search)\b": 2.4,
        r"\b(search results for|related to your search).*\b(exam|quiz|assignment|homework|syllabus)\b": 2.2,
    },
    "ai": {
        r"\b(chatgpt|openai|claude|gemini|copilot|perplexity|deepseek|llm|large language)\b": 3.0,
        r"\b(ask ai|ai assistant|generate answer|write an essay|prompt|regenerate response)\b": 2.5,
        r"\b(chat with|new conversation|send a message to ai|ai chatbot)\b": 2.0,
        r"\b(grammarly|quillbot|paraphrase|rewrite this|summarize this)\b": 1.8,
    },
    "cheating": {
        r"\b(chegg|course hero|studocu|brainly|bartleby|slader|numerade)\b": 3.5,
        r"\b(answer key|worked solution|step[- ]by[- ]step solution|homework help|unlock answers)\b": 2.8,
        r"\b(expert answer|tutor help|essay writer|plagiarism free|write my essay)\b": 2.5,
        r"\b(exam answers|test bank|solution manual|copy paste answer)\b": 2.5,
    },
    "entertainment": {
        r"\b(watch now|stream live|episode \d+|season \d+|movie|trailer|gaming)\b": 2.0,
        r"\b(youtube|netflix|spotify|twitch|tiktok|shorts|playlist|subscribe)\b": 2.2,
        r"\b(play game|leaderboard|free games|anime|manga)\b": 1.8,
    },
    "social": {
        r"\b(news feed|timeline|followers|following|retweet|like and share)\b": 2.0,
        r"\b(facebook|instagram|reddit|discord|whatsapp|telegram|messenger)\b": 2.2,
        r"\b(post a status|stories|direct message|group chat)\b": 1.6,
    },
}

_SIGNAL_BOOSTS: dict[str, tuple[str, float]] = {
    "has_chat_ui": ("ai", 2.5),
    "has_video_player": ("entertainment", 1.5),
    "has_code_editor": ("learning", 1.2),
    "has_quiz_form": ("exam", 1.0),
    "has_feed_ui": ("social", 1.5),
    "has_streaming_meta": ("entertainment", 2.0),
}

_TRACKER_CATEGORY_MAP = {
    "exam": "exam",
    "quiz": "quiz",
    "education": "education",
    "learning": "learning",
    "ai": "ai",
    "cheating": "cheating",
    "entertainment": "entertainment",
    "social": "social",
    "other": "other",
    # Transformer aliases
    "exam_platform": "exam",
    "educational": "education",
    "search_engine": "learning",
    "code_hosting": "learning",
    "social_media": "social",
    "ai_tool": "ai",
    "unknown": "other",
}

_RISK_LEVEL = {
    "exam": "none",
    "quiz": "none",
    "education": "none",
    "learning": "none",
    "ai": "high",
    "cheating": "critical",
    "entertainment": "critical",
    "social": "medium",
    "other": "medium",
}

_CATEGORY_RISK = {
    "exam": 3.0,
    "quiz": 2.0,
    "education": 5.0,
    "learning": 8.0,
    "ai": 72.0,
    "cheating": 95.0,
    "entertainment": 68.0,
    "social": 45.0,
    "other": 58.0,
}

_CATEGORY_EFFORT = {
    "exam": 98.0,
    "quiz": 96.0,
    "education": 94.0,
    "learning": 92.0,
    "ai": 25.0,
    "cheating": 8.0,
    "entertainment": 28.0,
    "social": 40.0,
    "other": 12.0,
}


@dataclass
class PageClassification:
    category: str
    tracker_category: str
    risk_level: str
    risk_score: float
    effort_score: float
    confidence: float
    method: str
    reason: str
    signals: dict[str, Any] = field(default_factory=dict)


def _normalize_text(*parts: str, limit: int = 8000) -> str:
    combined = " ".join(p for p in parts if p).lower()
    combined = re.sub(r"\s+", " ", combined)
    return combined[:limit]


def _score_text(text: str) -> dict[str, float]:
    scores = {key: 0.0 for key in _CATEGORY_PATTERNS}
    for category, patterns in _CATEGORY_PATTERNS.items():
        for pattern, weight in patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                scores[category] += weight
    return scores


def _signal_on(signals: dict[str, Any], *keys: str) -> bool:
    for key in keys:
        if signals.get(key):
            return True
    return False


def _apply_signal_boosts(scores: dict[str, float], signals: dict[str, Any]) -> None:
    if _signal_on(signals, "has_chat_ui", "hasChatUi"):
        scores["ai"] = scores.get("ai", 0.0) + 2.5
    if _signal_on(signals, "has_video_player", "hasVideoPlayer"):
        scores["entertainment"] = scores.get("entertainment", 0.0) + 1.5
    if _signal_on(signals, "has_code_editor", "hasCodeEditor"):
        scores["learning"] = scores.get("learning", 0.0) + 1.2
    if _signal_on(signals, "has_quiz_form", "hasQuizForm"):
        scores["quiz"] = scores.get("quiz", 0.0) + 3.0
    if _signal_on(signals, "has_education_ui", "hasEducationUi"):
        scores["education"] = scores.get("education", 0.0) + 3.0
    if _signal_on(signals, "has_feed_ui", "hasFeedUi"):
        scores["social"] = scores.get("social", 0.0) + 1.5
    if _signal_on(signals, "has_streaming_meta", "hasStreamingMeta"):
        scores["entertainment"] = scores.get("entertainment", 0.0) + 2.0

    meta = signals.get("meta") or {}
    if isinstance(meta, dict):
        og_type = str(meta.get("og:type") or meta.get("og_type") or "").lower()
        if "video" in og_type:
            scores["entertainment"] = scores.get("entertainment", 0.0) + 2.0
            signals["has_streaming_meta"] = True
        if any(token in og_type for token in ("course", "education", "article")):
            scores["education"] = scores.get("education", 0.0) + 2.0


def _classify_with_transformer(feature_text: str) -> dict[str, Any] | None:
    try:
        from services.transformer_analysis import get_transformer_analyzer

        analyzer = get_transformer_analyzer()
        if not getattr(analyzer, "_url_initialized", False):
            return None
        # Model expects URL-like input; feed compact page fingerprint
        snippet = feature_text[:512].replace("\n", " ")
        return analyzer.classify_url(snippet)
    except Exception:
        return None


def _local_exam_hint(url: str, text: str) -> bool:
    host = ""
    try:
        host = (urlparse(url).hostname or "").lower()
    except Exception:
        pass
    if host in {"localhost", "127.0.0.1"} or "examguard" in host:
        return True
    return bool(re.search(r"\b(examguard|proctor dashboard|live student feeds)\b", text))


def _is_exam_related_search(url: str, text: str) -> bool:
    combined = f"{url} {text}".lower()
    if not re.search(r"(/search|[?&]q=|google\.[^/]+/search|bing\.com/search|duckduckgo)", combined):
        return False

    study_terms = r"\b(exam|quiz|assignment|syllabus|lecture|homework|study|course|practice|textbook|notes|tutorial|problem set|lab)\b"

    try:
        parsed = urlparse(url if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", url) else f"https://{url.lstrip('/')}")
        qs = parse_qs(parsed.query)
        query_text = " ".join(qs.get("q", []) + qs.get("query", []))
        haystack = f"{query_text} {text}".lower()
        return bool(re.search(study_terms, haystack))
    except Exception:
        return bool(re.search(study_terms, combined))


def classify_page(
    url: str = "",
    title: str = "",
    content: str = "",
    signals: dict[str, Any] | None = None,
) -> PageClassification:
    """
    Classify any page from its visible content and JS/DOM signals.
    """
    signals = dict(signals or {})
    meta = signals.get("meta") or {}
    meta_text = " ".join(str(v) for v in meta.values()) if isinstance(meta, dict) else ""

    text = _normalize_text(url, title, content, meta_text)
    scores = _score_text(text)
    _apply_signal_boosts(scores, signals)

    if _is_exam_related_search(url, text):
        scores["learning"] = scores.get("learning", 0.0) + 4.5

    if _local_exam_hint(url, text):
        scores["exam"] = scores.get("exam", 0.0) + 5.0

    method = "content_heuristic"
    confidence = 0.45
    ml_result = _classify_with_transformer(text)
    if ml_result and ml_result.get("method") == "transformer" and ml_result.get("confidence", 0) > 0.55:
        ml_category = str(ml_result.get("category", "unknown"))
        ml_tracker = _TRACKER_CATEGORY_MAP.get(ml_category, "other")
        ml_conf = float(ml_result.get("confidence", 0.5))
        ml_risk = float(ml_result.get("risk_score", 0.2)) * 100.0
        # Blend ML with content scores
        scores[ml_tracker] = scores.get(ml_tracker, 0.0) + ml_conf * 4.0
        method = "transformer+content"
        confidence = max(confidence, ml_conf)

    best_category = max(scores, key=lambda k: scores[k])
    best_score = scores[best_category]

    if best_score < 1.0:
        best_category = "other"
        confidence = min(confidence, 0.35)

    tracker = _TRACKER_CATEGORY_MAP.get(best_category, "other")
    risk_score = _CATEGORY_RISK.get(tracker, 22.0)
    effort_score = _CATEGORY_EFFORT.get(tracker, 70.0)

    if ml_result and ml_result.get("method") == "transformer":
        ml_risk = float(ml_result.get("risk_score", 0.2)) * 100.0
        risk_score = (risk_score * 0.45) + (ml_risk * 0.55)

    confidence = min(0.98, confidence + min(best_score * 0.04, 0.25))

    top_hits = sorted(((k, v) for k, v in scores.items() if v > 0), key=lambda x: -x[1])[:4]
    reason = ", ".join(f"{cat}:{score:.1f}" for cat, score in top_hits) or "insufficient page signals"

    return PageClassification(
        category=best_category.upper(),
        tracker_category=tracker,
        risk_level=_RISK_LEVEL.get(tracker, "low"),
        risk_score=round(min(100.0, max(0.0, risk_score)), 1),
        effort_score=round(min(100.0, max(0.0, effort_score)), 1),
        confidence=round(confidence, 3),
        method=method,
        reason=reason,
        signals={
            "content_scores": scores,
            "ml": ml_result,
            "page_signals": signals,
        },
    )


def classify_for_tracker(url: str, title: str = "", content: str = "", signals: dict | None = None) -> dict[str, Any]:
    """Return dict compatible with extension browsingTracker."""
    result = classify_page(url, title, content, signals)
    return {
        "category": result.category,
        "trackerCategory": result.tracker_category,
        "site": (title or url)[:80],
        "riskLevel": result.risk_level,
        "riskScore": result.risk_score,
        "effortScore": result.effort_score,
        "confidence": result.confidence,
        "method": result.method,
        "reason": result.reason,
    }
