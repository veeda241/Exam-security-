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
from models.research import ResearchJourney
from api.schemas import EventData, EventBatch, EventResponse
from config import RISK_WEIGHTS, classify_url
from scoring.engine import ScoringEngine

router = APIRouter()


async def _update_session_stats(session: ExamSession, event_type: str):
    """Update session statistics based on event type"""
    evt = event_type.upper()
    if evt == "TAB_SWITCH":
        session.tab_switch_count += 1
    elif evt == "NAVIGATION":
        # Also count navigations as tab activity
        session.tab_switch_count += 1
    elif evt in ("COPY", "PASTE", "CUT"):
        session.copy_count += 1
    elif evt == "FACE_ABSENT":
        session.face_absence_count += 1
    elif evt in ("FORBIDDEN_SITE", "FORBIDDEN_CONTENT"):
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
        
        # Research Journey: track all navigation URLs with classification
        if event_data.type == "NAVIGATION" and event_data.data:
            nav_url = event_data.data.get('url', 'unknown')
            nav_title = event_data.data.get('title', 'unknown')
            url_class = classify_url(nav_url)
            category = "General"
            relevance = 0.5
            if url_class:
                category = url_class["category"]
                if category == "AI":
                    relevance = 0.1
                elif category == "CHEATING":
                    relevance = 0.0
                elif category == "ENTERTAINMENT":
                    relevance = 0.15
            journey_entry = ResearchJourney(
                session_id=batch.session_id,
                url=nav_url,
                title=nav_title,
                timestamp=datetime.fromtimestamp(event_data.timestamp / 1000.0),
                category=category,
                relevance_score=relevance,
            )
            db.add(journey_entry)
        
        # Track FORBIDDEN_SITE events in research journey
        if event_data.type == "FORBIDDEN_SITE" and event_data.data:
            forbidden_url = event_data.data.get('url', 'unknown')
            forbidden_category = event_data.data.get('category', 'Forbidden')
            if not any(e.type == "NAVIGATION" and e.data and e.data.get('url') == forbidden_url
                       for e in batch.events):
                journey_entry = ResearchJourney(
                    session_id=batch.session_id,
                    url=forbidden_url,
                    title=event_data.data.get('title', 'unknown'),
                    timestamp=datetime.fromtimestamp(event_data.timestamp / 1000.0),
                    category=forbidden_category,
                    relevance_score=0.0,
                )
                db.add(journey_entry)
        
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


@router.get("/session/{session_id}/visited-sites")
async def get_visited_sites(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get all websites visited during a session with categories"""
    
    result = await db.execute(
        select(ResearchJourney)
        .where(ResearchJourney.session_id == session_id)
        .order_by(ResearchJourney.timestamp.asc())
    )
    sites = result.scalars().all()
    
    # Build deduplicated site list
    visited = []
    seen_urls = set()
    
    for site in sites:
        url = site.url
        if url in seen_urls:
            continue
        seen_urls.add(url)
        visited.append({
            "url": url,
            "title": site.title,
            "category": site.category or "General",
            "relevance_score": site.relevance_score,
            "timestamp": site.timestamp.isoformat() if site.timestamp else None,
            "is_flagged": site.category in ("AI", "CHEATING", "ENTERTAINMENT", "Forbidden"),
        })
    
    # Summary stats
    categories = {}
    for v in visited:
        cat = v["category"]
        categories[cat] = categories.get(cat, 0) + 1
    
    flagged_count = sum(1 for v in visited if v["is_flagged"])
    
    return {
        "session_id": session_id,
        "total_sites": len(visited),
        "flagged_count": flagged_count,
        "category_breakdown": categories,
        "sites": visited,
    }
