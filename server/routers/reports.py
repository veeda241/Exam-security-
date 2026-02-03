"""
ExamGuard Pro - Reports API
Endpoints for generating and retrieving reports
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from pydantic import BaseModel
from typing import Optional, List
import json
import os

from database import get_db
from models.session import ExamSession
from models.event import Event
from models.analysis import AnalysisResult
from scoring.calculator import calculate_risk_score
from reports.generator import generate_pdf_report

router = APIRouter()


# ==================== Pydantic Models ====================

class ReportRequest(BaseModel):
    session_id: str
    include_screenshots: bool = False
    include_timeline: bool = True


class ReportSummary(BaseModel):
    session_id: str
    student_name: str
    exam_id: str
    duration_seconds: float
    risk_score: float
    risk_level: str
    event_counts: dict
    high_risk_events: List[dict]


# ==================== Endpoints ====================

@router.get("/session/{session_id}/summary", response_model=ReportSummary)
async def get_report_summary(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a summary report for a session"""
    
    # Get session
    result = await db.execute(
        select(ExamSession).where(ExamSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get high risk events (weight >= 15)
    events_result = await db.execute(
        select(Event)
        .where(Event.session_id == session_id)
        .where(Event.risk_weight >= 15)
        .order_by(Event.timestamp.desc())
        .limit(20)
    )
    high_risk_events = events_result.scalars().all()
    
    # Calculate duration
    end_time = session.ended_at or datetime.utcnow()
    duration = (end_time - session.started_at).total_seconds()
    
    return ReportSummary(
        session_id=session_id,
        student_name=session.student_name,
        exam_id=session.exam_id,
        duration_seconds=duration,
        risk_score=session.risk_score,
        risk_level=session.risk_level,
        event_counts={
            "tab_switches": session.tab_switch_count,
            "copy_events": session.copy_count,
            "face_absences": session.face_absence_count,
            "forbidden_sites": session.forbidden_site_count,
            "total": session.total_events,
        },
        high_risk_events=[e.to_dict() for e in high_risk_events],
    )


@router.get("/session/{session_id}/json")
async def get_json_report(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get full JSON report for a session"""
    
    # Get session
    result = await db.execute(
        select(ExamSession).where(ExamSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get all events
    events_result = await db.execute(
        select(Event)
        .where(Event.session_id == session_id)
        .order_by(Event.timestamp.asc())
    )
    events = events_result.scalars().all()
    
    # Get analysis results
    analysis_result = await db.execute(
        select(AnalysisResult)
        .where(AnalysisResult.session_id == session_id)
        .order_by(AnalysisResult.timestamp.asc())
    )
    analyses = analysis_result.scalars().all()
    
    # Calculate duration
    end_time = session.ended_at or datetime.utcnow()
    duration = (end_time - session.started_at).total_seconds()
    
    return {
        "report": {
            "generated_at": datetime.utcnow().isoformat(),
            "session": session.to_dict(),
            "duration_seconds": duration,
            "events": [e.to_dict() for e in events],
            "analysis_results": [a.to_dict() for a in analyses],
            "risk_breakdown": {
                "score": session.risk_score,
                "level": session.risk_level,
                "thresholds": {
                    "safe": "0-30",
                    "review": "30-60",
                    "suspicious": "60+",
                },
            },
        }
    }


@router.post("/session/{session_id}/pdf")
async def generate_pdf(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Generate PDF report for a session"""
    
    # Get session
    result = await db.execute(
        select(ExamSession).where(ExamSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get events
    events_result = await db.execute(
        select(Event)
        .where(Event.session_id == session_id)
        .order_by(Event.timestamp.asc())
    )
    events = events_result.scalars().all()
    
    # Generate PDF
    try:
        pdf_path = await generate_pdf_report(session, events)
        
        return {
            "success": True,
            "pdf_url": f"/uploads/reports/{os.path.basename(pdf_path)}",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")


@router.get("/flagged")
async def get_flagged_sessions(
    min_risk_score: float = 30,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """Get sessions with risk scores above threshold"""
    
    result = await db.execute(
        select(ExamSession)
        .where(ExamSession.risk_score >= min_risk_score)
        .order_by(ExamSession.risk_score.desc())
        .limit(limit)
    )
    sessions = result.scalars().all()
    
    return {
        "flagged_count": len(sessions),
        "sessions": [s.to_dict() for s in sessions],
    }
