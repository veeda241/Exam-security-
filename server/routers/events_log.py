"""
ExamGuard Pro - Events API
Endpoints for event logging
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from database import get_db
from models.session import ExamSession
from models.event import Event
from models.research import ResearchJourney
from config import RISK_WEIGHTS
from scoring.engine import ScoringEngine
from fastapi import BackgroundTasks

router = APIRouter()


# ==================== Pydantic Models ====================

class EventData(BaseModel):
    type: str
    timestamp: int  # Client JS timestamp
    data: Optional[Dict[str, Any]] = None
    id: Optional[str] = None


class EventBatch(BaseModel):
    session_id: str
    events: List[EventData]


class EventResponse(BaseModel):
    id: str
    session_id: str
    event_type: str
    timestamp: str
    risk_weight: int


# ==================== Endpoints ====================

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
    """Log multiple events at once"""
    
    # Verify session exists
    result = await db.execute(
        select(ExamSession).where(ExamSession.id == batch.session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    logged_count = 0
    
    for event_data in batch.events:
        # Get risk weight
        risk_weight = RISK_WEIGHTS.get(event_data.type, 0)
        
        # Create event
        new_event = Event(
            session_id=batch.session_id,
            event_type=event_data.type,
            client_timestamp=event_data.timestamp,
            data=event_data.data,
            risk_weight=risk_weight,
        )
        
        db.add(new_event)
        
        # Phase 10: Research Journey Integration
        if event_data.type == "NAVIGATION" and event_data.data:
            journey_entry = ResearchJourney(
                session_id=batch.session_id,
                url=event_data.data.get('url', 'unknown'),
                title=event_data.data.get('title', 'unknown'),
                timestamp=datetime.fromtimestamp(event_data.timestamp / 1000.0)
            )
            db.add(journey_entry)
        
        # Update session stats
        session.total_events += 1
        await _update_session_stats(session, event_data.type)
        
        logged_count += 1
    
    await db.commit()
    
    # Submit events to the real-time analysis pipeline for transformer processing
    try:
        from services.pipeline import get_pipeline
        pipeline = get_pipeline()
        for event_data in batch.events:
            await pipeline.submit({
                "type": event_data.type,
                "session_id": batch.session_id,
                "data": event_data.data or {},
                "timestamp": event_data.timestamp,
            })
    except Exception as e:
        print(f"[WARN] Pipeline submission failed: {e}")
    
    # Trigger score update in background
    background_tasks.add_task(ScoringEngine.update_session_scores, batch.session_id, db)
    
    return {
        "success": True,
        "events_logged": logged_count,
        "session_id": batch.session_id,
    }


@router.get("/session/{session_id}", response_model=List[EventResponse])
async def get_session_events(
    session_id: str,
    event_type: Optional[str] = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Get events for a session"""
    
    query = select(Event).where(Event.session_id == session_id).order_by(Event.timestamp.desc()).limit(limit)
    
    if event_type:
        query = query.where(Event.event_type == event_type)
    
    result = await db.execute(query)
    events = result.scalars().all()
    
    return [
        EventResponse(
            id=e.id,
            session_id=e.session_id,
            event_type=e.event_type,
            timestamp=e.timestamp.isoformat(),
            risk_weight=e.risk_weight,
        )
        for e in events
    ]


@router.get("/session/{session_id}/timeline")
async def get_event_timeline(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get full event timeline for a session"""
    
    result = await db.execute(
        select(Event).where(Event.session_id == session_id).order_by(Event.timestamp.asc())
    )
    events = result.scalars().all()
    
    return {
        "session_id": session_id,
        "event_count": len(events),
        "timeline": [e.to_dict() for e in events],
    }


# ==================== Helper Functions ====================

async def _update_session_stats(session: ExamSession, event_type: str):
    """Update session statistics based on event type"""
    
    if event_type == "TAB_SWITCH":
        session.tab_switch_count += 1
    elif event_type in ("COPY", "PASTE"):
        session.copy_count += 1
    elif event_type in ("FORBIDDEN_SITE", "FORBIDDEN_CONTENT"):
        session.forbidden_site_count += 1
    elif event_type == "FACE_ABSENT":
        session.face_absence_count += 1
