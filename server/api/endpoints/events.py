"""
ExamGuard Pro - Events Endpoint
API routes for event logging
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from typing import List

from database import get_db
from models.session import ExamSession
from models.event import Event
from api.schemas import EventData, EventBatch, EventResponse
from config import RISK_WEIGHTS
from scoring.engine import ScoringEngine

router = APIRouter()


async def _update_session_stats(session: ExamSession, event_type: str):
    """Update session statistics based on event type"""
    if event_type == "tab_switch":
        session.tab_switch_count += 1
    elif event_type in ["copy", "cut"]:
        session.copy_count += 1
    elif event_type == "face_not_found":
        session.face_absence_count += 1
    elif event_type == "forbidden_site":
        session.forbidden_site_count += 1


@router.post("/log", response_model=EventResponse)
async def log_event(
    session_id: str,
    event_data: EventData,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Log a single event"""
    
    # Verify session exists
    result = await db.execute(
        select(ExamSession).where(ExamSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get risk weight for event type
    risk_weight = RISK_WEIGHTS.get(event_data.type, 0)
    
    # Create event
    new_event = Event(
        session_id=session_id,
        event_type=event_data.type,
        client_timestamp=event_data.timestamp,
        data=event_data.data,
        risk_weight=risk_weight,
    )
    
    db.add(new_event)
    
    # Update session stats
    session.total_events += 1
    await _update_session_stats(session, event_data.type)
    
    await db.commit()
    await db.refresh(new_event)
    
    # Trigger score update in background
    background_tasks.add_task(ScoringEngine.update_session_scores, session_id, db)
    
    return EventResponse(
        id=new_event.id,
        session_id=session_id,
        event_type=new_event.event_type,
        timestamp=new_event.timestamp.isoformat(),
        risk_weight=risk_weight,
    )


@router.post("/batch")
async def log_events_batch(
    batch: EventBatch,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Log multiple events in a batch"""
    
    # Verify session exists
    result = await db.execute(
        select(ExamSession).where(ExamSession.id == batch.session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    logged_events = []
    
    for event_data in batch.events:
        risk_weight = RISK_WEIGHTS.get(event_data.type, 0)
        
        new_event = Event(
            session_id=batch.session_id,
            event_type=event_data.type,
            client_timestamp=event_data.timestamp,
            data=event_data.data,
            risk_weight=risk_weight,
        )
        
        db.add(new_event)
        session.total_events += 1
        await _update_session_stats(session, event_data.type)
        
        logged_events.append({
            "type": event_data.type,
            "risk_weight": risk_weight
        })
    
    await db.commit()
    
    # Trigger score update in background
    background_tasks.add_task(ScoringEngine.update_session_scores, batch.session_id, db)
    
    return {
        "success": True,
        "events_logged": len(logged_events),
        "events": logged_events
    }


@router.get("/session/{session_id}")
async def get_session_events(
    session_id: str,
    event_type: str = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Get all events for a session"""
    
    query = select(Event).where(Event.session_id == session_id)
    
    if event_type:
        query = query.where(Event.event_type == event_type)
    
    query = query.offset(skip).limit(limit).order_by(Event.timestamp.desc())
    
    result = await db.execute(query)
    events = result.scalars().all()
    
    return {
        "session_id": session_id,
        "total": len(events),
        "events": [e.to_dict() for e in events]
    }


@router.get("/session/{session_id}/timeline")
async def get_event_timeline(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get events as a timeline for visualization"""
    
    result = await db.execute(
        select(Event)
        .where(Event.session_id == session_id)
        .order_by(Event.timestamp.asc())
    )
    events = result.scalars().all()
    
    timeline = []
    for e in events:
        timeline.append({
            "id": e.id,
            "type": e.event_type,
            "timestamp": e.timestamp.isoformat(),
            "risk_weight": e.risk_weight,
            "data": e.data
        })
    
    return {
        "session_id": session_id,
        "timeline": timeline
    }
