"""
ExamGuard Pro - Reports Endpoint
API routes for generating and retrieving reports
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from typing import List
import os

from database import get_db
from models.session import ExamSession
from models.event import Event
from models.analysis import AnalysisResult
from api.schemas import ReportRequest, ReportSummary
from scoring.calculator import calculate_risk_score
from reports.generator import generate_pdf_report

router = APIRouter()


@router.get("/session/{session_id}/summary", response_model=ReportSummary)
async def get_report_summary(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a summary report for a session"""
    
    result = await db.execute(
        select(ExamSession).where(ExamSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get high risk events
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


@router.get("/session/{session_id}/pdf")
async def get_pdf_report(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Generate and download PDF report for a session"""
    
    result = await db.execute(
        select(ExamSession).where(ExamSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get events and analysis
    events_result = await db.execute(
        select(Event)
        .where(Event.session_id == session_id)
        .order_by(Event.timestamp.asc())
    )
    events = events_result.scalars().all()
    
    analysis_result = await db.execute(
        select(AnalysisResult)
        .where(AnalysisResult.session_id == session_id)
    )
    analyses = analysis_result.scalars().all()
    
    # Generate PDF
    try:
        pdf_path = await generate_pdf_report(
            session=session,
            events=events,
            analyses=analyses
        )
        
        return FileResponse(
            path=pdf_path,
            filename=f"report_{session_id}.pdf",
            media_type="application/pdf"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")


@router.get("/session/{session_id}/timeline")
async def get_session_timeline(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get event timeline for visualization"""
    
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
    
    # Build timeline with risk progression
    timeline = []
    cumulative_risk = 0
    
    for event in events:
        cumulative_risk += event.risk_weight
        timeline.append({
            "timestamp": event.timestamp.isoformat(),
            "event_type": event.event_type,
            "risk_weight": event.risk_weight,
            "cumulative_risk": cumulative_risk,
            "data": event.data
        })
    
    return {
        "session_id": session_id,
        "start_time": session.started_at.isoformat(),
        "end_time": session.ended_at.isoformat() if session.ended_at else None,
        "final_risk": session.risk_score,
        "timeline": timeline
    }
