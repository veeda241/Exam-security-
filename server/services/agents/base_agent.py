"""Shared data structures for the v2 agent scoring pipeline."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Sequence
from urllib.parse import urlparse
import re


def _pick(data: Mapping[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        value = data.get(key)
        if value not in (None, ""):
            return value
    return default


def _as_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _coerce_domains(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        items = [item.strip() for item in value.split(",")]
        return tuple(item for item in items if item)
    if isinstance(value, Sequence):
        return tuple(_as_text(item) for item in value if _as_text(item))
    return ()


def _normalize_host(url: str, fallback: str = "") -> str:
    if not url:
        return fallback.lower()

    candidate = url
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", candidate):
        candidate = f"https://{candidate.lstrip('/')}"

    try:
        parsed = urlparse(candidate)
        host = parsed.netloc or fallback
    except Exception:
        host = fallback

    host = host.lower()
    if host.startswith("www."):
        host = host[4:]
    return host


@dataclass(slots=True)
class PageContext:
    """Normalized request payload consumed by the agents."""

    session_id: str = ""
    student_id: str = ""
    url: str = ""
    domain_hint: str = ""
    path_hint: str = ""
    title: str = ""
    content: str = ""
    clipboard_text: str = ""
    youtube_title: str = ""
    youtube_channel: str = ""
    exam_subject: str = ""
    referrer: str = ""
    tab_duration_seconds: float = 0.0
    tab_switch_count: int = 0
    copy_count: int = 0
    paste_count: int = 0
    focus_lost_count: int = 0
    hidden_count: int = 0
    recent_domains: tuple[str, ...] = field(default_factory=tuple)
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def domain(self) -> str:
        return _normalize_host(self.url, self.domain_hint)

    @property
    def path(self) -> str:
        candidate = self.path_hint.strip()
        if candidate:
            return candidate if candidate.startswith("/") else f"/{candidate}"

        if not self.url:
            return ""

        if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", self.url):
            candidate_url = f"https://{self.url.lstrip('/')}"
        else:
            candidate_url = self.url

        try:
            return urlparse(candidate_url).path or ""
        except Exception:
            return ""

    @property
    def normalized_text(self) -> str:
        parts = [
            self.title,
            self.content,
            self.clipboard_text,
            self.youtube_title,
            self.youtube_channel,
            self.exam_subject,
            self.referrer,
        ]
        return " ".join(part.strip() for part in parts if part and part.strip()).lower()

    @property
    def domain_tokens(self) -> tuple[str, ...]:
        host = self.domain
        tokens = [token for token in re.split(r"[\W_]+", host) if token]
        path_tokens = [token for token in re.split(r"[\W_]+", self.path.lower()) if token]
        return tuple(tokens + path_tokens)

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "PageContext":
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")

        page_data: dict[str, Any] = {}
        nested = payload.get("page_context") or payload.get("context") or payload.get("pageContext")
        if isinstance(nested, Mapping):
            page_data.update({key: value for key, value in nested.items() if value not in (None, "")})

        for key, value in payload.items():
            if key not in {"page_context", "context", "pageContext"}:
                if value not in (None, ""):
                    page_data[key] = value

        extra = dict(page_data.get("extra") or {})
        for key in ("signals", "metadata", "page_metrics"):
            value = page_data.get(key)
            if isinstance(value, Mapping):
                extra.setdefault(key, dict(value))

        return cls(
            session_id=_as_text(_pick(page_data, "session_id", "sessionId")),
            student_id=_as_text(_pick(page_data, "student_id", "studentId")),
            url=_as_text(_pick(page_data, "url", "current_url", "currentUrl")),
            domain_hint=_as_text(_pick(page_data, "domain", "hostname", "host")),
            path_hint=_as_text(_pick(page_data, "path", "pathname")),
            title=_as_text(_pick(page_data, "title", "page_title", "pageTitle")),
            content=_as_text(
                _pick(page_data, "content", "body_text", "bodyText", "page_content", "pageContent", "text")
            ),
            clipboard_text=_as_text(_pick(page_data, "clipboard_text", "clipboardText", "copied_text", "copiedText")),
            youtube_title=_as_text(_pick(page_data, "youtube_title", "youtubeTitle")),
            youtube_channel=_as_text(_pick(page_data, "youtube_channel", "youtubeChannel")),
            exam_subject=_as_text(_pick(page_data, "exam_subject", "examSubject")),
            referrer=_as_text(_pick(page_data, "referrer", "referer")),
            tab_duration_seconds=_as_float(_pick(page_data, "tab_duration_seconds", "tabDurationSeconds")),
            tab_switch_count=_as_int(_pick(page_data, "tab_switch_count", "tabSwitchCount")),
            copy_count=_as_int(_pick(page_data, "copy_count", "copyCount")),
            paste_count=_as_int(_pick(page_data, "paste_count", "pasteCount")),
            focus_lost_count=_as_int(_pick(page_data, "focus_lost_count", "focusLostCount")),
            hidden_count=_as_int(_pick(page_data, "hidden_count", "hiddenCount")),
            recent_domains=_coerce_domains(_pick(page_data, "recent_domains", "recentDomains")),
            extra=extra,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "student_id": self.student_id,
            "url": self.url,
            "domain": self.domain,
            "path": self.path,
            "title": self.title,
            "content": self.content,
            "clipboard_text": self.clipboard_text,
            "youtube_title": self.youtube_title,
            "youtube_channel": self.youtube_channel,
            "exam_subject": self.exam_subject,
            "referrer": self.referrer,
            "tab_duration_seconds": self.tab_duration_seconds,
            "tab_switch_count": self.tab_switch_count,
            "copy_count": self.copy_count,
            "paste_count": self.paste_count,
            "focus_lost_count": self.focus_lost_count,
            "hidden_count": self.hidden_count,
            "recent_domains": list(self.recent_domains),
            "extra": dict(self.extra),
        }


@dataclass(slots=True)
class Verdict:
    """Single-agent verdict used by the orchestrator."""

    agent_name: str
    category: str
    label: str
    risk_score: float
    effort_score: float = 100.0
    confidence: float = 0.0
    reason: str = ""
    evidence: list[str] = field(default_factory=list)
    signals: dict[str, Any] = field(default_factory=dict)
    weight: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "category": self.category,
            "label": self.label,
            "risk_score": round(self.risk_score, 2),
            "effort_score": round(self.effort_score, 2),
            "confidence": round(self.confidence, 3),
            "reason": self.reason,
            "evidence": list(self.evidence),
            "signals": dict(self.signals),
            "weight": round(self.weight, 3),
        }


class AgentBase(ABC):
    """Base class for all scoring agents."""

    name = "agent"
    weight = 1.0

    @abstractmethod
    async def analyze(self, context: PageContext) -> Verdict:
        raise NotImplementedError

    @staticmethod
    def _clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
        return max(minimum, min(maximum, value))

    @staticmethod
    def _label_from_risk(risk_score: float) -> str:
        if risk_score >= 70.0:
            return "suspicious"
        if risk_score >= 30.0:
            return "review"
        return "safe"

    @staticmethod
    def _matches_any(text: str, needles: Sequence[str]) -> list[str]:
        lower = text.lower()
        return [needle for needle in needles if needle and needle.lower() in lower]

    @staticmethod
    def _token_overlap(left: str, right: str) -> float:
        left_tokens = {token for token in re.split(r"[\W_]+", left.lower()) if token}
        right_tokens = {token for token in re.split(r"[\W_]+", right.lower()) if token}
        if not left_tokens or not right_tokens:
            return 0.0
        return len(left_tokens & right_tokens) / max(len(left_tokens | right_tokens), 1)
