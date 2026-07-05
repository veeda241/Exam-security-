"""
ExamGuard Pro V2 — Centralized RiskEngine (pure function, no I/O).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Mapping


RiskLevel = Literal["safe", "review", "suspicious"]


@dataclass(frozen=True)
class Event:
    type: str
    weight: float = 0.0


@dataclass(frozen=True)
class RiskConfig:
    weights: Mapping[str, float]
    thresholds: Mapping[str, float]

    @classmethod
    def default(cls) -> RiskConfig:
        return cls(
            weights={
                "tab_switch": 10,
                "window_blur": 5,
                "copy_paste": 15,
                "face_missing": 20,
                "multiple_faces": 25,
                "gaze_away": 15,
                "ocr_flag": 40,
                "object_flag": 25,
                "text_similarity": 35,
                "forbidden_site": 40,
                "page_hidden": 8,
            },
            thresholds={"review": 30, "suspicious": 60},
        )


@dataclass(frozen=True)
class RiskResult:
    score: float
    level: RiskLevel
    breakdown: dict[str, float] = field(default_factory=dict)


def _normalize_event_type(event_type: str) -> str:
    return event_type.lower().replace("-", "_")


def compute_risk(events: list[Event], config: RiskConfig) -> RiskResult:
    """
    Deterministic risk scoring from ordered session events.

    Uses per-type weights from config; event.weight overrides when > 0.
    Idempotent for the same inputs.
    """
    breakdown: dict[str, float] = {}
    total = 0.0

    for event in events:
        key = _normalize_event_type(event.type)
        contribution = event.weight if event.weight > 0 else float(config.weights.get(key, 0))
        if contribution <= 0:
            continue
        breakdown[key] = breakdown.get(key, 0.0) + contribution
        total += contribution

    review_at = float(config.thresholds.get("review", 30))
    suspicious_at = float(config.thresholds.get("suspicious", 60))

    if total >= suspicious_at:
        level: RiskLevel = "suspicious"
    elif total >= review_at:
        level = "review"
    else:
        level = "safe"

    return RiskResult(score=round(total, 2), level=level, breakdown=breakdown)
