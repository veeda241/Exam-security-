"""
ExamGuard Pro - Sessions API
Endpoints for exam session management
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime
from pydantic import BaseModel
from typing import Optional, List

from database import get_db
from models.session import ExamSession
from scoring.calculator import calculate_risk_score

router = APIRouter()


# ==================== Pydantic Models ====================

class SessionCreate(BaseModel):
    student_id: str
    student_name: str
    exam_id: str


class SessionResponse(BaseModel):
    session_id: str
    student_id: str
    student_name: str
    exam_id: str
    started_at: str
    is_active: bool


class SessionSummary(BaseModel):
    id: str
    student_name: str
    student_id: str
    exam_id: str
    started_at: str
    ended_at: Optional[str]
    risk_score: float
    risk_level: str
    engagement_score: float
    content_relevance: float
    effort_alignment: float
    status: str
    stats: dict


# ==================== Endpoints ====================

@router.post("/create", response_model=SessionResponse)
async def create_session(
    session_data: SessionCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new exam session"""
    
    # Create new session
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
    
    # Get session
    result = await db.execute(
        select(ExamSession).where(ExamSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if not session.is_active:
        raise HTTPException(status_code=400, detail="Session already ended")
    
    # Calculate final risk score
    risk_score, risk_level = await calculate_risk_score(db, session_id)
    
    # Update session
    session.is_active = False
    session.ended_at = datetime.utcnow()
    session.risk_score = risk_score
    session.risk_level = risk_level
    
    await db.commit()
    
    return {
        "success": True,
        "session_id": session_id,
        "ended_at": session.ended_at.isoformat(),
        "risk_score": risk_score,
        "risk_level": risk_level,
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
    
    return SessionSummary(**session.to_dict())


@router.get("/", response_model=List[SessionSummary])
async def list_sessions(
    exam_id: Optional[str] = None,
    active_only: bool = False,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """List exam sessions with optional filtering"""
    
    query = select(ExamSession).order_by(ExamSession.started_at.desc()).limit(limit)
    
    if exam_id:
        query = query.where(ExamSession.exam_id == exam_id)
    
    if active_only:
        query = query.where(ExamSession.is_active == True)
    
    result = await db.execute(query)
    sessions = result.scalars().all()
    
    return [SessionSummary(**s.to_dict()) for s in sessions]


@router.get("/all", response_model=List[SessionSummary])
async def list_all_sessions(
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Alias for list_sessions to match frontend expecting /all"""
    return await list_sessions(limit=limit, db=db)


@router.get("/{session_id}/stats")
async def get_session_stats(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get detailed session statistics"""
    
    result = await db.execute(
        select(ExamSession).where(ExamSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Calculate duration
    end_time = session.ended_at or datetime.utcnow()
    duration_seconds = (end_time - session.started_at).total_seconds()
    
    return {
        "session_id": session_id,
        "duration_seconds": duration_seconds,
        "is_active": session.is_active,
        "risk_score": session.risk_score,
        "risk_level": session.risk_level,
        "events": {
            "tab_switches": session.tab_switch_count,
            "copy_events": session.copy_count,
            "face_absences": session.face_absence_count,
            "forbidden_sites": session.forbidden_site_count,
            "total": session.total_events,
        },
    }
