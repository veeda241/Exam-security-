"""
ExamGuard Pro - Risk Score Calculator
Calculates weighted risk scores from session events
"""

from typing import Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.event import Event
from models.session import ExamSession
from config import RISK_WEIGHTS, RISK_THRESHOLDS


async def calculate_risk_score(db: AsyncSession, session_id: str) -> Tuple[float, str]:
    """
    Calculate the risk score for a session
    
    Args:
        db: Database session
        session_id: Session ID to calculate score for
        
    Returns:
        Tuple of (risk_score, risk_level)
    """
    
    # Get all events for the session
    result = await db.execute(
        select(Event).where(Event.session_id == session_id)
    )
    events = result.scalars().all()
    
    # Calculate base score from event weights
    base_score = sum(event.risk_weight for event in events)
    
    # Get session for stats
    session_result = await db.execute(
        select(ExamSession).where(ExamSession.id == session_id)
    )
    session = session_result.scalar_one_or_none()
    
    # Apply bonus multipliers for repeated offenses
    multiplier = 1.0
    
    if session:
        # Multiple tab switches add bonus
        if session.tab_switch_count > 5:
            multiplier += 0.1 * (session.tab_switch_count - 5)
        
        # Multiple forbidden site accesses are very suspicious
        if session.forbidden_site_count > 1:
            multiplier += 0.2 * (session.forbidden_site_count - 1)
        
        # Frequent face absences
        if session.face_absence_count > 3:
            multiplier += 0.15 * (session.face_absence_count - 3)
    
    # Calculate final score
    final_score = min(base_score * multiplier, 100)
    
    # Determine risk level
    if final_score >= RISK_THRESHOLDS["REVIEW"]:
        risk_level = "suspicious"
    elif final_score >= RISK_THRESHOLDS["SAFE"]:
        risk_level = "review"
    else:
        risk_level = "safe"
    
    return round(final_score, 1), risk_level


def calculate_event_score(event_type: str, count: int = 1) -> int:
    """Calculate score for a specific event type"""
    base_weight = RISK_WEIGHTS.get(event_type, 0)
    return base_weight * count


def get_risk_breakdown(
    tab_switches: int,
    copy_events: int,
    face_absences: int,
    forbidden_sites: int,
    other_events: int = 0
) -> dict:
    """
    Get a breakdown of risk score by category
    
    Returns detailed contribution of each event type
    """
    
    breakdown = {
        "tab_switches": {
            "count": tab_switches,
            "weight": RISK_WEIGHTS.get("TAB_SWITCH", 10),
            "score": tab_switches * RISK_WEIGHTS.get("TAB_SWITCH", 10),
        },
        "copy_events": {
            "count": copy_events,
            "weight": RISK_WEIGHTS.get("COPY", 15),
            "score": copy_events * RISK_WEIGHTS.get("COPY", 15),
        },
        "face_absences": {
            "count": face_absences,
            "weight": RISK_WEIGHTS.get("FACE_ABSENT", 20),
            "score": face_absences * RISK_WEIGHTS.get("FACE_ABSENT", 20),
        },
        "forbidden_sites": {
            "count": forbidden_sites,
            "weight": RISK_WEIGHTS.get("FORBIDDEN_SITE", 40),
            "score": forbidden_sites * RISK_WEIGHTS.get("FORBIDDEN_SITE", 40),
        },
    }
    
    total = sum(cat["score"] for cat in breakdown.values())
    
    return {
        "breakdown": breakdown,
        "total_score": min(total, 100),
        "thresholds": RISK_THRESHOLDS,
    }
