"""
ExamGuard Pro - Sessions Endpoint
API routes for exam session management
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime
from typing import List

from database import get_db
from api.models import ExamSession
from api.schemas import SessionCreate, SessionResponse, SessionSummary
from scoring.calculator import calculate_risk_score

router = APIRouter()


@router.post("/create", response_model=SessionResponse)
async def create_session(
    session_data: SessionCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new exam session"""
    
    new_session = ExamSession(
        student_id=session_data.student_id,
        student_name=session_data.student_name,
        exam_id=session_data.exam_id,
    )
    
    db.add(new_session)
    await db.commit()
    await db.refresh(new_session)
    
    return SessionResponse(
        session_id=new_session.id,
        student_id=new_session.student_id,
        student_name=new_session.student_name,
        exam_id=new_session.exam_id,
        started_at=new_session.started_at.isoformat(),
        is_active=True,
    )


@router.post("/{session_id}/end")
async def end_session(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """End an exam session and calculate final risk score"""
    
    result = await db.execute(
        select(ExamSession).where(ExamSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if not session.is_active:
        raise HTTPException(status_code=400, detail="Session already ended")
    
    # End the session
    session.is_active = False
    session.ended_at = datetime.utcnow()
    
    # Calculate final risk score
    final_score = calculate_risk_score(session)
    session.risk_score = final_score
    
    # Set risk level
    if final_score >= 60:
        session.risk_level = "suspicious"
    elif final_score >= 30:
        session.risk_level = "review"
    else:
        session.risk_level = "safe"
    
    await db.commit()
    
    return {
        "session_id": session_id,
        "status": "ended",
        "final_risk_score": session.risk_score,
        "risk_level": session.risk_level,
        "duration_seconds": (session.ended_at - session.started_at).total_seconds()
    }


@router.get("/{session_id}", response_model=SessionSummary)
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get session details"""
    
    result = await db.execute(
        select(ExamSession).where(ExamSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return SessionSummary(
        id=session.id,
        student_name=session.student_name,
        student_id=session.student_id,
        exam_id=session.exam_id,
        started_at=session.started_at.isoformat(),
        ended_at=session.ended_at.isoformat() if session.ended_at else None,
        risk_score=session.risk_score,
        risk_level=session.risk_level,
        engagement_score=session.engagement_score,
        content_relevance=session.content_relevance,
        effort_alignment=session.effort_alignment,
        status="active" if session.is_active else "ended",
        stats={
            "tab_switches": session.tab_switch_count,
            "copy_events": session.copy_count,
            "face_absences": session.face_absence_count,
            "forbidden_sites": session.forbidden_site_count,
            "total": session.total_events
        }
    )


@router.get("/", response_model=List[SessionSummary])
async def list_sessions(
    active_only: bool = False,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Get all sessions with optional filtering"""
    
    query = select(ExamSession)
    
    if active_only:
        query = query.where(ExamSession.is_active == True)
    
    query = query.offset(skip).limit(limit).order_by(ExamSession.started_at.desc())
    
    result = await db.execute(query)
    sessions = result.scalars().all()
    
    return [
        SessionSummary(
            id=s.id,
            student_name=s.student_name,
            student_id=s.student_id,
            exam_id=s.exam_id,
            started_at=s.started_at.isoformat(),
            ended_at=s.ended_at.isoformat() if s.ended_at else None,
            risk_score=s.risk_score,
            risk_level=s.risk_level,
            engagement_score=s.engagement_score,
            content_relevance=s.content_relevance,
            effort_alignment=s.effort_alignment,
            status="active" if s.is_active else "ended",
            stats={
                "tab_switches": s.tab_switch_count,
                "copy_events": s.copy_count,
                "face_absences": s.face_absence_count,
                "forbidden_sites": s.forbidden_site_count,
                "total": s.total_events
            }
        )
        for s in sessions
    ]


@router.get("/active/count")
async def get_active_session_count(db: AsyncSession = Depends(get_db)):
    """Get count of active sessions"""
    
    result = await db.execute(
        select(ExamSession).where(ExamSession.is_active == True)
    )
    sessions = result.scalars().all()
    
    return {"active_count": len(sessions)}
