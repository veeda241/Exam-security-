from fastapi import APIRouter, HTTPException, BackgroundTasks
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
import asyncio

from supabase_client import get_supabase
from api.schemas import EventData, EventBatch, EventResponse
from config import RISK_WEIGHTS, classify_url

router = APIRouter()
supabase = get_supabase()


def _risk_level_from_score(score: float) -> str:
    if score >= 85:
        return "suspicious"
    if score >= 60:
        return "review"
    if score >= 30:
        return "medium"
    return "safe"


def _browsing_payload_from_event(data: Dict[str, Any]) -> Dict[str, Any]:
    active_site = data.get("activeSite") or data.get("active_site")
    if isinstance(active_site, dict):
        active_site = {
            "url": active_site.get("url") or "",
            "category": active_site.get("category") or active_site.get("siteCategory") or "other",
            "riskLevel": active_site.get("riskLevel") or active_site.get("risk_level") or "none",
            "title": active_site.get("title") or "",
        }

    return {
        "activeSite": active_site,
        "timeByCategory": data.get("timeByCategory") or {},
        "totalTime": data.get("totalTime", 0),
        "browsingRiskScore": float(data.get("browsingRiskScore", 0)),
        "effortScore": float(data.get("effortScore", 100)),
        "uniqueSitesVisited": data.get("uniqueSitesVisited", data.get("totalSitesVisited", 0)),
        "flaggedSitesCount": data.get("flaggedSitesCount", 0),
        "openTabsCount": data.get("openTabsCount", 0),
        "flaggedOpenTabs": data.get("flaggedOpenTabs", 0),
        "topFlaggedSites": data.get("topFlaggedSites") or [],
        "examTimePercent": data.get("examTimePercent", 0),
        "distractionTimePercent": data.get("distractionTimePercent", 0),
    }


def _apply_browsing_scores(session_updates: Dict[str, Any], data: Dict[str, Any]) -> None:
    browsing_risk = float(data.get("browsingRiskScore", 0))
    effort_score = float(data.get("effortScore", 100))
    session_updates["risk_score"] = round(min(100.0, max(0.0, browsing_risk)), 1)
    session_updates["engagement_score"] = round(min(100.0, max(0.0, effort_score)), 1)
    session_updates["effort_alignment"] = session_updates["engagement_score"]
    session_updates["risk_level"] = _risk_level_from_score(browsing_risk)
    session_updates["browsing"] = _browsing_payload_from_event(data)


def _get_local_session(session_id: str) -> Optional[Dict[str, Any]]:
    from api.endpoints import sessions as session_store

    with session_store._LOCAL_STORE_LOCK:
        session = session_store._LOCAL_SESSIONS.get(session_id)
        return dict(session) if session else None


def _update_local_session(session_id: str, updates: Dict[str, Any]) -> bool:
    from api.endpoints import sessions as session_store

    with session_store._LOCAL_STORE_LOCK:
        session = session_store._LOCAL_SESSIONS.get(session_id)
        if not session:
            return False
        session.update(updates)
        return True


def _resolve_session(session_id: str) -> Optional[Dict[str, Any]]:
    if supabase is not None:
        try:
            res = supabase.table("exam_sessions").select("*").eq("id", session_id).execute()
            if res.data:
                return res.data[0]
        except Exception as e:
            print(f"[Events] Supabase session lookup failed, using local fallback: {e}")
    return _get_local_session(session_id)

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
            score_updates: Dict[str, Any] = {}
            _apply_browsing_scores(score_updates, event_data.data)
            session = _resolve_session(session_id)
            if session:
                merged = {
                    "total_events": (session.get("total_events") or 0) + 1,
                    **score_updates,
                }
                if supabase is not None:
                    try:
                        supabase.table("exam_sessions").update(merged).eq("id", session_id).execute()
                    except Exception as db_err:
                        print(f"[Events] Supabase browsing update failed: {db_err}")
                        _update_local_session(session_id, merged)
                else:
                    _update_local_session(session_id, merged)

            return EventResponse(
                id=str(uuid.uuid4()),
                session_id=session_id,
                event_type=event_data.type,
                timestamp=datetime.utcnow().isoformat(),
                risk_weight=int(score_updates.get("risk_score", 0)),
            )

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
    """Log multiple events and update session scores (Supabase or local fallback)."""
    session_id = batch.session_id
    session = _resolve_session(session_id)
    if not session:
        print(f"[WARN] Session {session_id} not found - events will be dropped")
        return {"success": True, "events_logged": 0, "warning": "Session not found"}

    session_updates: Dict[str, Any] = {
        "total_events": (session.get("total_events") or 0) + len(batch.events),
    }
    logged_events: List[Dict[str, Any]] = []
    events_to_insert: List[Dict[str, Any]] = []
    research_entries: List[Dict[str, Any]] = []
    accumulated_risk = 0.0
    latest_browsing_data: Optional[Dict[str, Any]] = None

    for event_data in batch.events:
        evt_type = event_data.type
        evt_data = event_data.data or {}
        evt_ts = event_data.timestamp

        try:
            evt_ts = float(evt_ts) if evt_ts is not None else None
        except (TypeError, ValueError):
            evt_ts = None

        if evt_type == "BROWSING_SUMMARY":
            latest_browsing_data = evt_data
            logged_events.append({"type": evt_type, "risk_weight": int(evt_data.get("browsingRiskScore", 0))})
            continue

        risk_weight = RISK_WEIGHTS.get(evt_type, 0)
        category_risk = 0
        effort_impact = 0

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

        events_to_insert.append({
            "id": str(uuid.uuid4()),
            "session_id": session_id,
            "event_type": evt_type,
            "client_timestamp": int(evt_ts / 1000) if evt_ts else int(datetime.utcnow().timestamp()),
            "data": evt_data,
            "risk_weight": int(max(risk_weight, category_risk)),
            "timestamp": datetime.utcnow().isoformat(),
        })

        stat_field = _get_session_update_field(evt_type)
        if stat_field:
            session_updates[stat_field] = (session_updates.get(stat_field) or session.get(stat_field) or 0) + 1

        if evt_type in ("NAVIGATION", "TAB_SWITCH") and evt_data:
            nav_url = evt_data.get("url", "unknown")
            nav_title = evt_data.get("title", "unknown")
            url_class = classify_url(nav_url, nav_title)

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
                elif category in ("EDUCATION", "LEARNING", "EXAM"):
                    relevance = 0.9
                elif category == "SOCIAL":
                    relevance = 0.2

            research_entries.append({
                "id": str(uuid.uuid4()),
                "session_id": session_id,
                "url": nav_url,
                "title": nav_title,
                "timestamp": datetime.fromtimestamp(evt_ts / 1000.0).isoformat() if evt_ts else datetime.utcnow().isoformat(),
                "category": category,
                "relevance_score": relevance,
            })

        logged_events.append({
            "type": evt_type,
            "risk_weight": int(max(risk_weight, category_risk)),
        })

    if latest_browsing_data:
        _apply_browsing_scores(session_updates, latest_browsing_data)
        behavioral_risk = min(100.0, accumulated_risk * 0.25)
        session_updates["risk_score"] = min(
            100.0,
            float(session_updates.get("risk_score", 0)) + behavioral_risk,
        )
        session_updates["risk_level"] = _risk_level_from_score(float(session_updates["risk_score"]))
    else:
        current_risk = float(session.get("risk_score") or 0.0)
        current_effort = float(session.get("engagement_score") or session.get("effort_alignment") or 100.0)
        session_updates["risk_score"] = min(100.0, current_risk + accumulated_risk)
        session_updates["risk_level"] = _risk_level_from_score(float(session_updates["risk_score"]))
        session_updates["engagement_score"] = max(0.0, current_effort)
        session_updates["effort_alignment"] = session_updates["engagement_score"]

    if supabase is not None and events_to_insert:
        try:
            supabase.table("events").insert(events_to_insert).execute()
        except Exception as e:
            print(f"[Events] Failed to insert events: {e}")

    if supabase is not None and research_entries:
        try:
            supabase.table("research_journey").insert(research_entries).execute()
        except Exception as e:
            print(f"[Events] Failed to insert research entries: {e}")

    if supabase is not None:
        try:
            supabase.table("exam_sessions").update(session_updates).eq("id", session_id).execute()
        except Exception as e:
            print(f"[Events] Supabase session update failed, using local fallback: {e}")
            _update_local_session(session_id, session_updates)
    else:
        _update_local_session(session_id, session_updates)

    try:
        from services.realtime import get_realtime_manager

        mgr = get_realtime_manager()
        target_room = session.get("exam_id") or session_id
        await mgr.broadcast_to_session(
            target_room,
            {
                "type": "risk_score_update",
                "session_id": session_id,
                "student_id": session.get("student_id"),
                "risk_score": session_updates.get("risk_score"),
                "engagement_score": session_updates.get("engagement_score"),
                "effort_score": session_updates.get("engagement_score"),
                "risk_level": session_updates.get("risk_level"),
                "browsing": session_updates.get("browsing"),
            },
        )
    except Exception as ws_err:
        print(f"[Events] Score broadcast failed: {ws_err}")

    return {
        "success": True,
        "events_logged": len(logged_events),
        "events": logged_events,
    }


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
