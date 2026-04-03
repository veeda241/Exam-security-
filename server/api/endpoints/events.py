from fastapi import APIRouter, HTTPException, BackgroundTasks
import uuid
from datetime import datetime
from typing import List
import asyncio

from supabase_client import get_supabase
from api.schemas import EventData, EventBatch, EventResponse
from config import RISK_WEIGHTS, classify_url

router = APIRouter()
supabase = get_supabase()

def _get_session_update_field(event_type: str):
    """Map event type to session stat column"""
    evt = event_type.upper()
    if evt in ("TAB_SWITCH", "NAVIGATION"):
        return "tab_switch_count"
    elif evt in ("COPY", "PASTE", "CUT"):
        return "copy_count"
    elif evt == "FACE_ABSENT":
        return "face_absence_count"
    elif evt == "MULTIPLE_FACES":
        return "multiface_count"
    elif evt in ("FORBIDDEN_SITE", "FORBIDDEN_CONTENT"):
        return "forbidden_site_count"
    return None


@router.post("/log", response_model=EventResponse)
async def log_event(
    session_id: str,
    event_data: EventData,
    background_tasks: BackgroundTasks
):
    """Log an event and update session metrics in Supabase"""
    
    try:
        # Determine base risk weight
        risk_weight = RISK_WEIGHTS.get(event_data.type, 0)
        
        # Enhanced tracking: for summaries, look at categories
        category_risk = 0
        effort_impact = 0
        
        if event_data.type == "BROWSING_SUMMARY" and event_data.data:
            # Use the browsingRiskScore and effortScore directly from extension
            browsing_risk = event_data.data.get("browsingRiskScore", 0)
            effort_score = event_data.data.get("effortScore", 100)
            
            # Add browsing risk to category_risk
            category_risk += browsing_risk * 0.1  # Scale down to avoid double counting
            
            # If effort is low, penalize
            if effort_score < 50:
                effort_impact += (50 - effort_score) * 0.1
            
            # Also check categories if present
            categories = event_data.data.get("categories", [])
            
            # Penalize entertainment/cheating in summary
            if any(c in categories for c in ("Entertainment", "Social", "Shopping")):
                category_risk += 15
                effort_impact += 10
            if any(c in categories for c in ("Cheating", "AI", "Academic")):
                category_risk += 40
                effort_impact += 25
            
            # Check for flagged sites
            flagged_count = event_data.data.get("flaggedSitesCount", 0)
            category_risk += min(flagged_count * 5, 30)  # Up to 30 risk for flagged sites

        # Record the event
        res = supabase.table("events").insert({
            "id": str(uuid.uuid4()),
            "session_id": session_id,
            "event_type": event_data.type,
            "client_timestamp": int(event_data.timestamp / 1000) if event_data.timestamp else int(datetime.utcnow().timestamp()),
            "data": event_data.data,
            "risk_weight": int(max(risk_weight, category_risk)),
            "timestamp": datetime.utcnow().isoformat()
        }).execute()
        
        if not res.data:
            raise HTTPException(status_code=500, detail="Log failed")
        
        new_event = res.data[0]
        
        # Update Session with dynamic totals and risk
        session_res = supabase.table("exam_sessions").select("*").eq("id", session_id).execute()
        if session_res.data:
            session = session_res.data[0]
            
            # Calculate new scores
            added_risk = max(risk_weight, category_risk)
            current_risk = float(session.get("risk_score") or 0.0)
            new_risk = min(100.0, current_risk + added_risk)
            
            # Effort Alignment (slowly decrease if bad things happen, or if idle)
            current_effort = float(session.get("engagement_score") or session.get("effort_alignment") or 100.0)
            
            if event_data.type == "INPUT_IDLE":
                effort_impact += 5
            elif event_data.type in ("TAB_SWITCH", "NAVIGATION"):
                effort_impact += 3
            elif event_data.type in ("COPY", "PASTE"):
                effort_impact += 5
                
            new_effort = max(0.0, current_effort - effort_impact)
            
            # Map risk to level
            risk_level = "safe"
            if new_risk > 80: risk_level = "critical"
            elif new_risk > 60: risk_level = "high"
            elif new_risk > 30: risk_level = "medium"
            
            updates = {
                "total_events": (session.get("total_events") or 0) + 1,
                "risk_score": new_risk,
                "risk_level": risk_level,
                "engagement_score": new_effort,
                "effort_alignment": new_effort
            }
            
            # Field-specific stats
            stat_field = _get_session_update_field(event_data.type)
            if stat_field:
                updates[stat_field] = (session.get(stat_field) or 0) + 1
            
            supabase.table("exam_sessions").update(updates).eq("id", session_id).execute()
        
        return EventResponse(
            id=new_event["id"],
            session_id=session_id,
            event_type=new_event["event_type"],
            timestamp=new_event["timestamp"],
            risk_weight=max(risk_weight, category_risk),
        )
    except Exception as e:
        print(f"[RE-LOG ERROR] {e}")
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
            # Session might have been ended/deleted - return success anyway to prevent extension retry loops
            print(f"[WARN] Session {session_id} not found - events will be dropped")
            return {"success": True, "events_logged": 0, "warning": "Session not found"}
        
        session = session_res.data[0]
        session_updates = {"total_events": (session.get("total_events") or 0) + len(batch.events)}
        
        logged_events = []
        events_to_insert = []
        research_entries = []
        # Scoring Accumulators
        accumulated_risk = 0.0
        accumulated_effort_impact = 0.0
        
        for event_data in batch.events:
            evt_type = event_data.type
            evt_data = event_data.data or {}
            evt_ts = event_data.timestamp
            
            # Safely handle timestamp - ensure it's a number
            try:
                if evt_ts is not None:
                    evt_ts = float(evt_ts)
            except (TypeError, ValueError):
                evt_ts = None
            
            risk_weight = RISK_WEIGHTS.get(evt_type, 0)
            category_risk = 0
            effort_impact = 0
            
            if evt_type == "BROWSING_SUMMARY":
                # Use the browsingRiskScore and effortScore directly from extension
                browsing_risk = evt_data.get("browsingRiskScore", 0)
                effort_score = evt_data.get("effortScore", 100)
                
                # Add browsing risk to accumulated risk
                category_risk += browsing_risk * 0.1  # Scale down to avoid double counting
                
                # If effort is low, penalize
                if effort_score < 50:
                    effort_impact += (50 - effort_score) * 0.1
                
                # Also check categories if present
                categories = evt_data.get("categories", [])
                if any(c in categories for c in ("Entertainment", "Social", "Shopping")):
                    category_risk += 15
                    effort_impact += 10
                if any(c in categories for c in ("Cheating", "AI", "Academic")):
                    category_risk += 40
                    effort_impact += 25
                
                # Check for flagged sites
                flagged_count = evt_data.get("flaggedSitesCount", 0)
                category_risk += min(flagged_count * 5, 30)  # Up to 30 risk for flagged sites
            
            if evt_type == "INPUT_IDLE":
                effort_impact += 5
            elif evt_type in ("TAB_SWITCH", "NAVIGATION"):
                effort_impact += 3
            elif evt_type in ("COPY", "PASTE", "PHONE_DETECTED", "MULTIPLE_FACES", "FACE_ABSENT"):
                effort_impact += 5
            elif evt_type in ("WINDOW_BLUR", "PAGE_HIDDEN"):
                effort_impact += 3
                category_risk += 3
                
            accumulated_risk += max(risk_weight, category_risk)
            accumulated_effort_impact += effort_impact

            events_to_insert.append({
                "id": str(uuid.uuid4()),
                "session_id": session_id,
                "event_type": evt_type,
                "client_timestamp": int(evt_ts / 1000) if evt_ts else int(datetime.utcnow().timestamp()),
                "data": evt_data,
                "risk_weight": int(max(risk_weight, category_risk)),
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Update local session state for batch
            stat_field = _get_session_update_field(evt_type)
            if stat_field:
                session_updates[stat_field] = (session_updates.get(stat_field) or session.get(stat_field) or 0) + 1

            # Research Journey tracking
            if evt_type in ("NAVIGATION", "TAB_SWITCH") and evt_data:
                nav_url = evt_data.get('url', 'unknown')
                nav_title = evt_data.get('title', 'unknown')
                url_class = classify_url(nav_url)
                
                category = "General"
                relevance = 0.5
                
                if url_class:
                    category = url_class.get("category", "General")
                    if category == "AI": relevance = 0.1
                    elif category == "CHEATING": relevance = 0.0
                    elif category == "ENTERTAINMENT": relevance = 0.15
                    elif category == "EDUCATION": relevance = 0.9
                    elif category == "SOCIAL": relevance = 0.2
                
                research_entries.append({
                    "id": str(uuid.uuid4()),
                    "session_id": session_id,
                    "url": nav_url,
                    "title": nav_title,
                    "timestamp": datetime.fromtimestamp(evt_ts / 1000.0).isoformat() if evt_ts else datetime.utcnow().isoformat(),
                    "category": category,
                    "relevance_score": relevance
                })
            
            logged_events.append({
                "type": evt_type,
                "risk_weight": int(max(risk_weight, category_risk))
            })
            
        # Bulk Insert
        if events_to_insert:
            try:
                supabase.table("events").insert(events_to_insert).execute()
            except Exception as e:
                print(f"[ERROR] Failed to insert events: {e}")
        if research_entries:
            try:
                supabase.table("research_journey").insert(research_entries).execute()
            except Exception as e:
                print(f"[WARN] Failed to insert research entries: {e}")
            
        # Calculate final session scores explicitly in the batch
        current_risk = float(session.get("risk_score") or 0.0)
        new_risk = min(100.0, current_risk + accumulated_risk)
        
        current_effort = float(session.get("engagement_score") or session.get("effort_alignment") or 100.0)
        new_effort = max(0.0, current_effort - accumulated_effort_impact)
        
        risk_level = "safe"
        if new_risk > 80: risk_level = "critical"
        elif new_risk > 60: risk_level = "high"
        elif new_risk > 30: risk_level = "medium"
        
        session_updates.update({
            "risk_score": new_risk,
            "risk_level": risk_level,
            "engagement_score": new_effort,
            "effort_alignment": new_effort
        })
        
        # Update Session exactly once
        try:
            supabase.table("exam_sessions").update(session_updates).eq("id", session_id).execute()
        except Exception as e:
            print(f"[WARN] Failed to update session: {e}")

        
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
        import traceback
        print(f"[ERROR] Events batch failed: {e}")
        traceback.print_exc()
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
