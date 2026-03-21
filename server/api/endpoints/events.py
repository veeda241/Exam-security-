from fastapi import APIRouter, HTTPException, BackgroundTasks
import uuid
from datetime import datetime
from typing import List

from supabase_client import get_supabase
from api.schemas import EventData, EventBatch, EventResponse
from config import RISK_WEIGHTS, classify_url

router = APIRouter()
supabase = get_supabase()

def _get_session_update_field(event_type: str):
    """Map event type to session stat column"""
    evt = event_type.upper()
    if evt == "TAB_SWITCH" or evt == "NAVIGATION":
        return "tab_switch_count"
    elif evt in ("COPY", "PASTE", "CUT"):
        return "copy_count"
    elif evt == "FACE_ABSENT":
        return "face_absence_count"
    elif evt in ("FORBIDDEN_SITE", "FORBIDDEN_CONTENT"):
        return "forbidden_site_count"
    return None


@router.post("/log", response_model=EventResponse)
async def log_event(
    session_id: str,
    event_data: EventData,
    background_tasks: BackgroundTasks
):
    """Log a single event via Supabase"""
    
    try:
        # Get risk weight
        risk_weight = RISK_WEIGHTS.get(event_data.type, 0)
        
        # Create event in Supabase
        res = supabase.table("events").insert({
            "id": str(uuid.uuid4()),
            "session_id": session_id,
            "event_type": event_data.type,
            "client_timestamp": int(event_data.timestamp / 1000) if event_data.timestamp else int(datetime.utcnow().timestamp()),
            "data": event_data.data,
            "risk_weight": risk_weight,
            "timestamp": datetime.utcnow().isoformat()
        }).execute()
        
        if not res.data:
            raise HTTPException(status_code=500, detail="Failed to log event")
        
        new_event = res.data[0]
        
        # Update session stats (async-ish)
        stat_field = _get_session_update_field(event_data.type)
        
        # We need to get current stats first (or use a stored procedure if available)
        session_res = supabase.table("exam_sessions").select("*").eq("id", session_id).execute()
        if session_res.data:
            session = session_res.data[0]
            updates = {"total_events": (session.get("total_events") or 0) + 1}
            if stat_field:
                updates[stat_field] = (session.get(stat_field) or 0) + 1
            
            supabase.table("exam_sessions").update(updates).eq("id", session_id).execute()
        
        return EventResponse(
            id=new_event["id"],
            session_id=session_id,
            event_type=new_event["event_type"],
            timestamp=new_event["timestamp"],
            risk_weight=risk_weight,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch")
async def log_events_batch(
    batch: EventBatch,
    background_tasks: BackgroundTasks
):
    """Log multiple events in a batch via Supabase"""
    
    try:
        session_id = batch.session_id
        
        # Get session current state
        session_res = supabase.table("exam_sessions").select("*").eq("id", session_id).execute()
        if not session_res.data:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = session_res.data[0]
        session_updates = {"total_events": (session.get("total_events") or 0) + len(batch.events)}
        
        logged_events = []
        events_to_insert = []
        research_entries = []
        
        for event_data in batch.events:
            risk_weight = RISK_WEIGHTS.get(event_data.type, 0)
            
            events_to_insert.append({
                "id": str(uuid.uuid4()),
                "session_id": session_id,
                "event_type": event_data.type,
                "client_timestamp": int(event_data.timestamp / 1000) if event_data.timestamp else int(datetime.utcnow().timestamp()),
                "data": event_data.data,
                "risk_weight": risk_weight,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Update local session state for batch
            stat_field = _get_session_update_field(event_data.type)
            if stat_field:
                session_updates[stat_field] = (session_updates.get(stat_field) or session.get(stat_field) or 0) + 1

            # Research Journey tracking (record both full navigations and tab switches)
            if event_data.type in ("NAVIGATION", "TAB_SWITCH") and event_data.data:
                nav_url = event_data.data.get('url', 'unknown')
                nav_title = event_data.data.get('title', 'unknown')
                url_class = classify_url(nav_url)
                
                category = "General"
                relevance = 0.5
                
                if url_class:
                    category = url_class.get("category", "General")
                    if category == "AI": 
                        relevance = 0.1
                    elif category == "CHEATING": 
                        relevance = 0.0
                    elif category == "ENTERTAINMENT": 
                        relevance = 0.15
                    elif category == "EDUCATION":
                        relevance = 0.9
                    elif category == "SOCIAL":
                        relevance = 0.2
                
                research_entries.append({
                    "session_id": session_id,
                    "url": nav_url,
                    "title": nav_title,
                    "timestamp": datetime.fromtimestamp(event_data.timestamp / 1000.0).isoformat(),
                    "category": category,
                    "relevance_score": relevance
                })
            
            logged_events.append({
                "type": event_data.type,
                "risk_weight": risk_weight
            })
            
        # Bulk Insert
        if events_to_insert:
            supabase.table("events").insert(events_to_insert).execute()
        if research_entries:
            supabase.table("research_journey").insert(research_entries).execute()
            
        # Update Session
        supabase.table("exam_sessions").update(session_updates).eq("id", session_id).execute()
        
        # Submit events to the real-time analysis pipeline
        try:
            from services.pipeline import get_pipeline
            pipeline = get_pipeline()
            # If the pipeline is running, submit events
            if pipeline._running:
                for event_data in batch.events:
                    # We pass the same structure as event_log version for compatibility
                    await pipeline.submit({
                        "type": event_data.type,
                        "session_id": session_id,
                        "data": event_data.data or {},
                        "timestamp": event_data.timestamp,
                    })
        except Exception as e:
            print(f"[WARN] Pipeline submission failed in Supabase router: {e}")
        
        return {
            "success": True,
            "events_logged": len(logged_events),
            "events": logged_events
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}")
async def get_session_events(
    session_id: str,
    event_type: str = None,
    limit: int = 100
):
    """Get events for a session from Supabase"""
    
    try:
        query = supabase.table("events").select("*").eq("session_id", session_id).order("timestamp", desc=True).limit(limit)
        if event_type:
            query = query.eq("event_type", event_type)
            
        res = query.execute()
        return {
            "session_id": session_id,
            "total": len(res.data),
            "events": res.data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}/timeline")
async def get_event_timeline(session_id: str):
    """Get event timeline from Supabase"""
    try:
        res = supabase.table("events").select("*").eq("session_id", session_id).order("timestamp", desc=False).execute()
        return {
            "session_id": session_id,
            "timeline": res.data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}/visited-sites")
async def get_visited_sites(session_id: str):
    """Get visited sites from Supabase"""
    try:
        res = supabase.table("research_journey").select("*").eq("session_id", session_id).order("timestamp", desc=False).execute()
        sites = res.data
        
        visited = []
        seen_urls = set()
        categories = {}
        
        for s in sites:
            url = s["url"]
            if url in seen_urls: continue
            seen_urls.add(url)
            
            cat = s.get("category", "General")
            is_flagged = cat in ("AI", "CHEATING", "ENTERTAINMENT", "Forbidden")
            
            visited.append({
                "url": url,
                "title": s.get("title"),
                "category": cat,
                "relevance_score": s.get("relevance_score", 0.5),
                "timestamp": s.get("timestamp"),
                "is_flagged": is_flagged
            })
            
            categories[cat] = categories.get(cat, 0) + 1
            
        return {
            "session_id": session_id,
            "total_sites": len(visited),
            "flagged_count": sum(1 for v in visited if v["is_flagged"]),
            "category_breakdown": categories,
            "sites": visited
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
