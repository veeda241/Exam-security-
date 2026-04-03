"""
ExamGuard Pro - Scoring Engine
Calculates engagement, relevance, effort, and risk metrics.

Uses BROWSING_SUMMARY events from the chrome.tabs tracker for
time-on-site and per-category browsing analysis.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.analysis import AnalysisResult
from models.event import Event
from models.session import ExamSession
from services.anomaly import get_detector

log = logging.getLogger(__name__)


# ── Scoring constants ─────────────────────────────────────────────────────────

class _Engagement:
    BASE                  = 100.0
    FACE_ABSENCE_MAX      = 40.0   # penalty cap for face absence ratio
    TAB_SWITCH_PER        = 2.0    # points per switch
    TAB_SWITCH_MAX        = 30.0
    WINDOW_BLUR_PER       = 5.0    # points per blur event
    WINDOW_BLUR_MAX       = 20.0
    DISTRACTION_THRESHOLD = 10.0   # % distraction before penalty starts
    DISTRACTION_PER       = 0.8    # points per % above threshold
    DISTRACTION_MAX       = 25.0
    FLAGGED_TAB_PER       = 3.0    # points per flagged open tab
    FLAGGED_TAB_MAX       = 15.0


class _Relevance:
    BASE                  = 100.0
    FORBIDDEN_PER         = 25.0
    FORBIDDEN_MAX         = 100.0
    OCR_FORBIDDEN_PER     = 10.0
    BROWSE_MIN_TIME_MS    = 30_000  # skip browsing penalty below 30 s
    EXAM_TIME_THRESHOLD   = 50.0    # % exam time before penalty kicks in
    EXAM_TIME_PER         = 0.6
    EXAM_TIME_MAX         = 30.0


class _Effort:
    NEUTRAL_BASE          = 60.0   # used when no browsing data available
    OTHER_SITE_CREDIT     = 0.10   # 10 % credit for "other" sites
    PRODUCTIVE_BONUS_TIME = 30.0   # 1 % per N seconds of productive time
    PRODUCTIVE_RATIO_BONUS = 20.0  # bonus when productive ratio > 50 %
    PRODUCTIVE_RATIO_THRESHOLD = 0.5
    BROWSE_MIN_MS         = 5_000  # minimum browse data to trust ratios
    ACTIVITY_GOOD_MIN     = 2.0    # events/min considered active
    ACTIVITY_GOOD_MAX     = 15.0   # above this = suspicious spam
    ACTIVITY_GOOD_BONUS   = 15.0
    ACTIVITY_SPAM_PENALTY = 10.0
    COPY_GRACE            = 5      # free copy events before penalty
    COPY_PER_EXCESS       = 5.0
    # Per-category forbidden site penalties
    AI_PER                = 5.0;  AI_MAX            = 25.0
    ENTERTAINMENT_PER     = 3.0;  ENTERTAINMENT_MAX = 15.0
    CHEATING_PER          = 8.0;  CHEATING_MAX      = 30.0
    GENERAL_PER           = 5.0;  GENERAL_MAX       = 25.0
    # Blending weight for extension's own effort score
    EXT_WEIGHT            = 0.30


class _Risk:
    VISION_WEIGHT    = 0.30
    OCR_WEIGHT       = 0.20
    ANOMALY_WEIGHT   = 0.20
    BROWSING_WEIGHT  = 0.30
    DISTRACTION_MULT = 1.50  # scales distraction % into a risk score
    # Forbidden-site bonus caps (added on top of weighted sum)
    AI_BONUS_PER          = 5.0
    CHEATING_BONUS_PER    = 8.0
    ENTERTAINMENT_BONUS_PER = 3.0
    FORBIDDEN_BONUS_MAX   = 25.0
    FLAGGED_TAB_PER       = 5.0
    FLAGGED_TAB_MAX       = 20.0
    # Risk level thresholds
    SAFE_BELOW       = 30.0
    REVIEW_BELOW     = 60.0
    FLAG_ABOVE       = 70.0


# ── Internal data containers ──────────────────────────────────────────────────

@dataclass
class _BrowsingData:
    """Parsed fields from the latest BROWSING_SUMMARY event."""
    time_by_category:     Dict[str, float] = field(default_factory=dict)
    total_time_ms:        float = 0.0
    exam_time_pct:        float = 0.0
    distraction_time_pct: float = 0.0
    ext_browsing_risk:    float = 0.0
    ext_effort_score:     float = 100.0   # extension default = fully productive
    flagged_sites_count:  int   = 0
    flagged_open_tabs:    int   = 0

    @classmethod
    def from_summary(cls, data: Dict[str, Any]) -> "_BrowsingData":
        return cls(
            time_by_category     = data.get("timeByCategory", {}),
            total_time_ms        = float(data.get("totalTime", 0)),
            exam_time_pct        = float(data.get("examTimePercent", 0)),
            distraction_time_pct = float(data.get("distractionTimePercent", 0)),
            ext_browsing_risk    = float(data.get("browsingRiskScore", 0)),
            ext_effort_score     = float(data.get("effortScore", 100)),
            flagged_sites_count  = int(data.get("flaggedSitesCount", 0)),
            flagged_open_tabs    = int(data.get("flaggedOpenTabs", 0)),
        )

    @classmethod
    def empty(cls) -> "_BrowsingData":
        return cls()

    def category_ms(self, *keys: str) -> float:
        return sum(self.time_by_category.get(k, 0.0) for k in keys)


@dataclass
class _ForbiddenCounts:
    ai:          int = 0
    entertainment: int = 0
    cheating:    int = 0
    general:     int = 0   # forbidden events with no recognised category

    @property
    def total(self) -> int:
        return self.ai + self.entertainment + self.cheating + self.general


# ── Helper extractors ─────────────────────────────────────────────────────────

def _latest_browsing_summary(events: Sequence[Event]) -> _BrowsingData:
    summaries = [e for e in events if e.event_type == "BROWSING_SUMMARY" and e.data]
    if not summaries:
        return _BrowsingData.empty()
    latest = max(summaries, key=lambda e: e.client_timestamp or 0)
    return _BrowsingData.from_summary(latest.data)


def _session_duration_seconds(session: ExamSession) -> float:
    if not session.started_at:
        return 60.0
    end = session.ended_at or datetime.utcnow()
    return max((end - session.started_at).total_seconds(), 1.0)


def _forbidden_counts(events: Sequence[Event]) -> _ForbiddenCounts:
    counts = _ForbiddenCounts()
    for e in events:
        if e.event_type != "FORBIDDEN_SITE":
            continue
        category = (e.data or {}).get("category", "").upper()
        if category == "AI":
            counts.ai += 1
        elif category == "ENTERTAINMENT":
            counts.entertainment += 1
        elif category == "CHEATING":
            counts.cheating += 1
        else:
            counts.general += 1
    return counts


def _latest_tab_audit_flagged(events: Sequence[Event]) -> int:
    audits = [e for e in events if e.event_type == "TAB_AUDIT" and e.data]
    if not audits:
        return 0
    latest = max(audits, key=lambda e: e.client_timestamp or 0)
    return int(latest.data.get("flaggedTabs", 0))


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def _penalty(value: float, per: float, cap: float) -> float:
    """Scale a raw count into a penalty, never exceeding `cap`."""
    return min(value * per, cap)


# ── Score calculators (pure, no I/O) ─────────────────────────────────────────

def _calc_engagement(
    session:      ExamSession,
    analyses:     Sequence[AnalysisResult],
    events:       Sequence[Event],
    browsing:     _BrowsingData,
) -> float:
    E = _Engagement
    score = E.BASE

    # Face absence
    face = [a for a in analyses if a.analysis_type == "FACE_DETECTION"]
    if face:
        absent_ratio = sum(1 for a in face if not a.face_detected) / len(face)
        score -= absent_ratio * E.FACE_ABSENCE_MAX

    # Tab switching
    score -= _penalty(session.tab_switch_count, E.TAB_SWITCH_PER, E.TAB_SWITCH_MAX)

    # Window blur events
    blur_count = sum(1 for e in events if e.event_type == "WINDOW_BLUR")
    score -= _penalty(blur_count, E.WINDOW_BLUR_PER, E.WINDOW_BLUR_MAX)

    # Browsing distraction time
    excess_distraction = max(browsing.distraction_time_pct - E.DISTRACTION_THRESHOLD, 0.0)
    score -= _penalty(excess_distraction, E.DISTRACTION_PER, E.DISTRACTION_MAX)

    # Flagged open tabs
    score -= _penalty(browsing.flagged_open_tabs, E.FLAGGED_TAB_PER, E.FLAGGED_TAB_MAX)

    return _clamp(score)


def _calc_relevance(
    session:  ExamSession,
    analyses: Sequence[AnalysisResult],
    browsing: _BrowsingData,
) -> float:
    R = _Relevance
    score = R.BASE

    # Forbidden site visits
    score -= _penalty(session.forbidden_site_count, R.FORBIDDEN_PER, R.FORBIDDEN_MAX)

    # OCR forbidden keyword hits
    ocr_hits = sum(
        1 for a in analyses
        if a.analysis_type == "OCR"
        and (a.result_data or {}).get("forbidden_detected")
    )
    score -= ocr_hits * R.OCR_FORBIDDEN_PER

    # Browsing: penalise low exam-platform time (only with enough data)
    if browsing.total_time_ms > R.BROWSE_MIN_TIME_MS:
        deficit = max(R.EXAM_TIME_THRESHOLD - browsing.exam_time_pct, 0.0)
        score -= _penalty(deficit, R.EXAM_TIME_PER, R.EXAM_TIME_MAX)

    return _clamp(score)


def _calc_effort(
    session:   ExamSession,
    events:    Sequence[Event],
    browsing:  _BrowsingData,
    forbidden: _ForbiddenCounts,
) -> float:
    E = _Effort

    exam_ms        = browsing.category_ms("exam")
    learning_ms    = browsing.category_ms("learning")
    ai_ms          = browsing.category_ms("ai")
    cheating_ms    = browsing.category_ms("cheating")
    entertainment_ms = browsing.category_ms("entertainment")
    other_ms       = browsing.category_ms("other")

    productive_ms  = exam_ms + learning_ms
    total_ms       = productive_ms + ai_ms + cheating_ms + entertainment_ms + other_ms

    if total_ms > E.BROWSE_MIN_MS:
        productive_ratio = productive_ms / total_ms
        other_ratio      = other_ms / total_ms

        score  = productive_ratio * 100
        score += other_ratio * (E.OTHER_SITE_CREDIT * 100)

        # Bonus for raw productive time
        score += (productive_ms / 1000.0) / E.PRODUCTIVE_BONUS_TIME

        if productive_ratio > E.PRODUCTIVE_RATIO_THRESHOLD:
            score += E.PRODUCTIVE_RATIO_BONUS
    else:
        # Fallback: activity-rate heuristic when browsing data is sparse
        duration_min  = _session_duration_seconds(session) / 60.0
        epm           = len(events) / max(duration_min, 1.0)
        score         = E.NEUTRAL_BASE

        if E.ACTIVITY_GOOD_MIN <= epm < E.ACTIVITY_GOOD_MAX:
            score += E.ACTIVITY_GOOD_BONUS
        elif epm >= E.ACTIVITY_GOOD_MAX:
            score -= E.ACTIVITY_SPAM_PENALTY

    # Copy/paste excess
    copy_excess = max(session.copy_count - E.COPY_GRACE, 0)
    score -= copy_excess * E.COPY_PER_EXCESS

    # Per-category forbidden penalties
    score -= _penalty(forbidden.ai,            E.AI_PER,            E.AI_MAX)
    score -= _penalty(forbidden.entertainment, E.ENTERTAINMENT_PER, E.ENTERTAINMENT_MAX)
    score -= _penalty(forbidden.cheating,      E.CHEATING_PER,      E.CHEATING_MAX)
    score -= _penalty(forbidden.general,       E.GENERAL_PER,       E.GENERAL_MAX)

    # Blend with extension's own effort estimate
    score = score * (1 - E.EXT_WEIGHT) + browsing.ext_effort_score * E.EXT_WEIGHT

    return _clamp(score)


def _calc_risk(
    session:           ExamSession,
    analyses:          Sequence[AnalysisResult],
    events:            Sequence[Event],
    browsing:          _BrowsingData,
    forbidden:         _ForbiddenCounts,
    content_relevance: float,
    anomaly_score:     float,
) -> float:
    R = _Risk

    vision_impact  = sum(
        a.risk_score_added for a in analyses
        if a.analysis_type == "LIVE_VISION_ALERT"
    )
    ocr_impact     = 100.0 - content_relevance

    # Browsing risk: blend extension score with server-side distraction %
    time_based_risk = 0.0
    if browsing.total_time_ms > 0:
        time_based_risk = _clamp(browsing.distraction_time_pct * R.DISTRACTION_MULT)
    browsing_risk = (browsing.ext_browsing_risk + time_based_risk) / 2.0

    # Extra risk from flagged open tabs (latest TAB_AUDIT)
    flagged_tabs  = _latest_tab_audit_flagged(events)
    browsing_risk = _clamp(browsing_risk + _penalty(flagged_tabs, R.FLAGGED_TAB_PER, R.FLAGGED_TAB_MAX))

    # Weighted aggregate
    agg = (
        vision_impact  * R.VISION_WEIGHT   +
        ocr_impact     * R.OCR_WEIGHT      +
        anomaly_score  * R.ANOMALY_WEIGHT  +
        browsing_risk  * R.BROWSING_WEIGHT
    )

    # Additive forbidden-site bonus (on top of weighted score)
    forbidden_bonus = _clamp(
        forbidden.ai            * R.AI_BONUS_PER
        + forbidden.cheating    * R.CHEATING_BONUS_PER
        + forbidden.entertainment * R.ENTERTAINMENT_BONUS_PER,
        hi=R.FORBIDDEN_BONUS_MAX,
    )

    return _clamp(agg + forbidden_bonus)


def _apply_risk_level(session: ExamSession) -> None:
    R = _Risk
    score = session.risk_score
    if score < R.SAFE_BELOW:
        session.risk_level = "safe"
    elif score < R.REVIEW_BELOW:
        session.risk_level = "review"
    else:
        session.risk_level = "suspicious"

    if score > R.FLAG_ABOVE:
        session.status = "flagged"


# ── Public engine ─────────────────────────────────────────────────────────────

class ScoringEngine:
    """
    Orchestrates all scoring passes for an exam session.

    All score calculators are pure functions; this class is responsible only
    for I/O (loading from DB, committing results) and wiring them together.
    """

    @staticmethod
    async def update_session_scores(session_id: str, db: AsyncSession) -> None:
        """Load session data, recalculate every metric, persist to DB."""

        # ── Load data ──────────────────────────────────────────────────────
        session_row = await db.execute(
            select(ExamSession).where(ExamSession.id == session_id)
        )
        session: Optional[ExamSession] = session_row.scalar_one_or_none()
        if not session:
            log.warning("update_session_scores: session %s not found", session_id)
            return

        events_row = await db.execute(
            select(Event).where(Event.session_id == session_id)
        )
        events: List[Event] = events_row.scalars().all()

        analyses_row = await db.execute(
            select(AnalysisResult).where(AnalysisResult.session_id == session_id)
        )
        analyses: List[AnalysisResult] = analyses_row.scalars().all()

        # ── Pre-process shared inputs ──────────────────────────────────────
        browsing  = _latest_browsing_summary(events)
        forbidden = _forbidden_counts(events)

        duration_s = _session_duration_seconds(session)

        # Anomaly detection (external service — kept as-is)
        detector       = get_detector()
        anomaly_result = detector.analyze_session_behavior(
            [e.to_dict() for e in events], duration_s
        )
        anomaly_score  = float(anomaly_result.get("risk_score", 0))

        # ── Score calculations ─────────────────────────────────────────────
        session.engagement_score = _calc_engagement(session, analyses, events, browsing)
        session.content_relevance = _calc_relevance(session, analyses, browsing)
        session.effort_alignment = _calc_effort(session, events, browsing, forbidden)

        session.risk_score = _calc_risk(
            session       = session,
            analyses      = analyses,
            events        = events,
            browsing      = browsing,
            forbidden     = forbidden,
            content_relevance = session.content_relevance,
            anomaly_score = anomaly_score,
        )

        _apply_risk_level(session)

        log.info(
            "Scores updated — session=%s engagement=%.1f relevance=%.1f "
            "effort=%.1f risk=%.1f level=%s",
            session_id,
            session.engagement_score,
            session.content_relevance,
            session.effort_alignment,
            session.risk_score,
            session.risk_level,
        )

        await db.commit()