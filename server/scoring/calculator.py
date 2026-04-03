"""
ExamGuard Pro - Risk Score Calculator
Calculates weighted risk scores from session events.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import RISK_THRESHOLDS, RISK_WEIGHTS
from models.event import Event
from models.session import ExamSession

log = logging.getLogger(__name__)


# ── Constants ─────────────────────────────────────────────────────────────────

# Thresholds for repeat-offence multiplier bonuses
_TAB_SWITCH_GRACE     = 5    # free tab switches before penalty kicks in
_FORBIDDEN_SITE_GRACE = 1    # one forbidden site before escalation
_FACE_ABSENCE_GRACE   = 3    # face absences before escalation

_TAB_SWITCH_BONUS     = 0.10  # +10 % per switch above grace
_FORBIDDEN_SITE_BONUS = 0.20  # +20 % per site above grace
_FACE_ABSENCE_BONUS   = 0.15  # +15 % per absence above grace

MAX_SCORE = 100.0


# ── Data models ───────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class CategoryScore:
    """Score contribution from a single event category."""
    count:  int
    weight: float
    score:  float   # = count × weight (pre-cap)

    @classmethod
    def compute(cls, event_key: str, count: int) -> "CategoryScore":
        weight = float(RISK_WEIGHTS.get(event_key, 0))
        return cls(count=count, weight=weight, score=count * weight)


@dataclass
class RiskBreakdown:
    """Full breakdown of how a risk score was composed."""
    tab_switches:    CategoryScore
    copy_events:     CategoryScore
    face_absences:   CategoryScore
    forbidden_sites: CategoryScore
    other_events:    CategoryScore = field(default_factory=lambda: CategoryScore(0, 0.0, 0.0))

    multiplier:  float = 1.0
    raw_score:   float = 0.0   # pre-cap sum × multiplier
    final_score: float = 0.0   # capped at MAX_SCORE
    risk_level:  str   = "safe"

    @property
    def categories(self) -> dict[str, CategoryScore]:
        return {
            "tab_switches":    self.tab_switches,
            "copy_events":     self.copy_events,
            "face_absences":   self.face_absences,
            "forbidden_sites": self.forbidden_sites,
            "other_events":    self.other_events,
        }

    def to_dict(self) -> dict:
        return {
            "breakdown": {
                name: {
                    "count":  cat.count,
                    "weight": cat.weight,
                    "score":  cat.score,
                }
                for name, cat in self.categories.items()
            },
            "multiplier":   round(self.multiplier, 4),
            "raw_score":    round(self.raw_score, 2),
            "final_score":  round(self.final_score, 1),
            "risk_level":   self.risk_level,
            "thresholds":   RISK_THRESHOLDS,
        }


# ── Core logic ────────────────────────────────────────────────────────────────

def _repeat_offence_multiplier(
    tab_switch_count:    int,
    forbidden_site_count: int,
    face_absence_count:  int,
) -> float:
    """
    Returns a multiplier >= 1.0 that escalates for repeated behaviour.
    Each violation type contributes independently above its grace threshold.
    """
    bonus = 0.0

    excess_tabs = max(0, tab_switch_count - _TAB_SWITCH_GRACE)
    bonus += excess_tabs * _TAB_SWITCH_BONUS

    excess_sites = max(0, forbidden_site_count - _FORBIDDEN_SITE_GRACE)
    bonus += excess_sites * _FORBIDDEN_SITE_BONUS

    excess_face = max(0, face_absence_count - _FACE_ABSENCE_GRACE)
    bonus += excess_face * _FACE_ABSENCE_BONUS

    return 1.0 + bonus


def _classify_risk(score: float) -> str:
    """Map a numeric score to a risk label using configured thresholds."""
    if score >= RISK_THRESHOLDS["REVIEW"]:
        return "suspicious"
    if score >= RISK_THRESHOLDS["SAFE"]:
        return "review"
    return "safe"


def build_breakdown(
    tab_switches:    int,
    copy_events:     int,
    face_absences:   int,
    forbidden_sites: int,
    other_events:    int = 0,
) -> RiskBreakdown:
    """
    Pure function — no I/O. Computes a full RiskBreakdown from raw counts.
    Safe to call in tests, Celery tasks, or anywhere else without a DB.
    """
    cats = RiskBreakdown(
        tab_switches    = CategoryScore.compute("TAB_SWITCH",     tab_switches),
        copy_events     = CategoryScore.compute("COPY",           copy_events),
        face_absences   = CategoryScore.compute("FACE_ABSENT",    face_absences),
        forbidden_sites = CategoryScore.compute("FORBIDDEN_SITE", forbidden_sites),
        other_events    = CategoryScore.compute("OTHER",          other_events),
    )

    base_score  = sum(c.score for c in cats.categories.values())
    multiplier  = _repeat_offence_multiplier(tab_switches, forbidden_sites, face_absences)
    raw_score   = base_score * multiplier
    final_score = min(raw_score, MAX_SCORE)

    cats.multiplier  = multiplier
    cats.raw_score   = raw_score
    cats.final_score = final_score
    cats.risk_level  = _classify_risk(final_score)

    return cats


# ── Database-backed functions ─────────────────────────────────────────────────

async def calculate_risk_score(
    db: AsyncSession,
    session_id: str,
) -> Tuple[float, str]:
    """
    Calculate the risk score for a session by loading its events from the DB.

    Returns:
        (final_score, risk_level)
    """
    events_result = await db.execute(
        select(Event).where(Event.session_id == session_id)
    )
    events: list[Event] = events_result.scalars().all()

    if not events:
        log.debug("No events found for session %s — score is 0.0 / safe", session_id)
        return 0.0, "safe"

    session_result = await db.execute(
        select(ExamSession).where(ExamSession.id == session_id)
    )
    session: ExamSession | None = session_result.scalar_one_or_none()

    if session is None:
        log.warning("Session %s not found; computing score from raw events only", session_id)

    # Count event types from the events table (single source of truth)
    counts: dict[str, int] = {}
    for event in events:
        counts[event.event_type] = counts.get(event.event_type, 0) + 1

    breakdown = build_breakdown(
        tab_switches    = counts.get("TAB_SWITCH",     0),
        copy_events     = counts.get("COPY",           0),
        face_absences   = counts.get("FACE_ABSENT",    0),
        forbidden_sites = counts.get("FORBIDDEN_SITE", 0),
        other_events    = counts.get("OTHER",          0),
    )

    log.info(
        "Session %s — score=%.1f level=%s multiplier=%.2f",
        session_id, breakdown.final_score, breakdown.risk_level, breakdown.multiplier,
    )

    return round(breakdown.final_score, 1), breakdown.risk_level


async def get_risk_breakdown(
    db: AsyncSession,
    session_id: str,
) -> dict:
    """
    Return a fully serialisable breakdown dict for a session.
    Useful for API responses and report generation.
    """
    events_result = await db.execute(
        select(Event).where(Event.session_id == session_id)
    )
    events: list[Event] = events_result.scalars().all()

    counts: dict[str, int] = {}
    for event in events:
        counts[event.event_type] = counts.get(event.event_type, 0) + 1

    breakdown = build_breakdown(
        tab_switches    = counts.get("TAB_SWITCH",     0),
        copy_events     = counts.get("COPY",           0),
        face_absences   = counts.get("FACE_ABSENT",    0),
        forbidden_sites = counts.get("FORBIDDEN_SITE", 0),
        other_events    = counts.get("OTHER",          0),
    )

    return breakdown.to_dict()


# ── Stateless helpers (no DB needed) ─────────────────────────────────────────

def score_single_event(event_type: str, count: int = 1) -> float:
    """Return the raw score contribution for `count` occurrences of an event."""
    if count < 0:
        raise ValueError(f"count must be >= 0, got {count}")
    return CategoryScore.compute(event_type, count).score


def score_from_counts(
    tab_switches:    int = 0,
    copy_events:     int = 0,
    face_absences:   int = 0,
    forbidden_sites: int = 0,
    other_events:    int = 0,
) -> dict:
    """
    Lightweight wrapper around build_breakdown() for callers that
    already have counts but no DB session (e.g. unit tests, simulations).
    """
    return build_breakdown(
        tab_switches    = tab_switches,
        copy_events     = copy_events,
        face_absences   = face_absences,
        forbidden_sites = forbidden_sites,
        other_events    = other_events,
    ).to_dict()