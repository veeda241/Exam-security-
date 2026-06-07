from fastapi import APIRouter, HTTPException
from supabase_client import get_supabase
from datetime import datetime
from threading import Lock
from typing import Any, Dict, List
import uuid

from api.schemas import SessionCreate, SessionResponse, SessionSummary

router = APIRouter()
supabase = get_supabase()

# Local development fallback store. This keeps the dashboard usable when Supabase
# is unavailable or the workstation cannot resolve the Supabase host.
_LOCAL_STORE_LOCK = Lock()
_LOCAL_STUDENTS: Dict[str, Dict[str, Any]] = {}
_LOCAL_SESSIONS: Dict[str, Dict[str, Any]] = {}


def _session_stats(session: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "tab_switches": session.get("tab_switch_count", 0),
        "copy_events": session.get("copy_count", 0),
        "face_absences": session.get("face_absence_count", 0),
        "forbidden_sites": session.get("forbidden_site_count", 0),
        "total": session.get("total_events", 0),
    }


def _local_student_name(student_id: str) -> str:
    student = _LOCAL_STUDENTS.get(student_id)
    if not student:
        return "Unknown"
    return student.get("name") or "Unknown"


def _build_proctor_lookup(sessions: List[Dict[str, Any]]) -> Dict[str, str]:
    lookup: Dict[str, str] = {}
    for session in sessions:
        student_id = str(session.get("student_id") or "")
        exam_id = session.get("exam_id")
        if student_id.startswith("PROCTOR-") and exam_id and exam_id not in lookup:
            lookup[exam_id] = session.get("id")
    return lookup


def _resolve_proctor_session_id(session: Dict[str, Any], proctor_lookup: Dict[str, str]) -> str | None:
    student_id = str(session.get("student_id") or "")
    if student_id.startswith("PROCTOR-"):
        return session.get("id")
    return proctor_lookup.get(session.get("exam_id"))


def _build_local_summary(session: Dict[str, Any], proctor_session_id: str | None = None) -> SessionSummary:
    return SessionSummary(
        id=session["id"],
        student_name=_local_student_name(session["student_id"]),
        student_id=session["student_id"],
        exam_id=session["exam_id"],
        proctor_session_id=proctor_session_id,
        started_at=session["started_at"],
        ended_at=session.get("ended_at"),
        risk_score=session.get("risk_score", 0.0),
        risk_level=session.get("risk_level", "safe"),
        engagement_score=session.get("engagement_score", 100.0),
        content_relevance=session.get("content_relevance", 100.0),
        effort_alignment=session.get("effort_alignment", 100.0),
        status="active" if session.get("is_active", True) else "ended",
        stats=_session_stats(session),
        browsing=session.get("browsing") or _latest_browsing_summary(session.get("id", "")),
    )


def _latest_browsing_summary(session_id: str) -> Dict[str, Any] | None:
    try:
        res = (
            supabase.table("events")
            .select("data, timestamp")
            .eq("session_id", session_id)
            .eq("event_type", "BROWSING_SUMMARY")
            .order("timestamp", desc=True)
            .limit(1)
            .execute()
        )

        if not getattr(res, "data", None):
            return None

        payload = res.data[0].get("data") or {}
        if not isinstance(payload, dict):
            return None

        active_site = payload.get("activeSite") or payload.get("active_site") or None
        if isinstance(active_site, dict):
            active_site = {
                "url": active_site.get("url") or "",
                "category": active_site.get("category") or active_site.get("siteCategory") or "other",
                "riskLevel": active_site.get("riskLevel") or active_site.get("risk_level") or "none",
                "title": active_site.get("title") or "",
            }

        return {
            "activeSite": active_site,
            "timeByCategory": payload.get("timeByCategory") or {},
            "totalTime": payload.get("totalTime", 0),
            "browsingRiskScore": payload.get("browsingRiskScore", 0),
            "effortScore": payload.get("effortScore", 100),
            "uniqueSitesVisited": payload.get("uniqueSitesVisited", payload.get("totalSitesVisited", 0)),
            "flaggedSitesCount": payload.get("flaggedSitesCount", 0),
            "openTabsCount": payload.get("openTabsCount", 0),
            "flaggedOpenTabs": payload.get("flaggedOpenTabs", 0),
            "currentCategory": payload.get("currentCategory") or (active_site or {}).get("category") if isinstance(active_site, dict) else payload.get("currentCategory", "none"),
            "topFlaggedSites": payload.get("topFlaggedSites") or [],
        }
    except Exception as e:
        print(f"[Session] Failed to load latest browsing summary for {session_id}: {e}")
        return None


def _store_local_student(student_id: str, student_name: str, email: str | None = None) -> None:
    with _LOCAL_STORE_LOCK:
        existing = _LOCAL_STUDENTS.get(student_id, {})
        _LOCAL_STUDENTS[student_id] = {
            "id": student_id,
            "name": student_name or existing.get("name") or "Unknown",
            "email": email or existing.get("email"),
            "created_at": existing.get("created_at") or datetime.utcnow().isoformat(),
        }


def _create_local_session(session_data: SessionCreate) -> SessionResponse:
    target_exam_id = session_data.exam_id.strip()
    print(f"[Session] Student trying to join exam_id: '{target_exam_id}' as '{session_data.student_id}'")

    creating_proctor = session_data.student_id.startswith("PROCTOR-")
    with _LOCAL_STORE_LOCK:
        if not creating_proctor:
            matched_proctor = next(
                (
                    session
                    for session in _LOCAL_SESSIONS.values()
                    if session["student_id"].startswith("PROCTOR-")
                    and session["exam_id"].lower() == target_exam_id.lower()
                ),
                None,
            )
            if matched_proctor:
                session_data.exam_id = matched_proctor["exam_id"]
                print(f"[Session] APPROVED: Student joined existing exam '{session_data.exam_id}'")
            else:
                print(f"[Session] INFO: Student joined '{target_exam_id}' before proctor. Allowing lazy-activation.")

    _store_local_student(
        session_data.student_id,
        session_data.student_name,
        session_data.student_email or f"{session_data.student_id}@examguard.internal",
    )

    # End any stale active sessions for the same student/exam to avoid duplicate feeds.
    if not creating_proctor:
        ended_at = datetime.utcnow().isoformat()
        with _LOCAL_STORE_LOCK:
            for existing in _LOCAL_SESSIONS.values():
                if (
                    existing.get("is_active", True)
                    and existing.get("student_id") == session_data.student_id
                    and existing.get("exam_id") == session_data.exam_id
                ):
                    existing["is_active"] = False
                    existing["ended_at"] = ended_at
                    existing["status"] = "ended"

    session_id = str(uuid.uuid4())
    started_at = datetime.utcnow().isoformat()
    local_session = {
        "id": session_id,
        "student_id": session_data.student_id,
        "exam_id": session_data.exam_id,
        "is_active": True,
        "started_at": started_at,
        "ended_at": None,
        "risk_score": 0.0,
        "risk_level": "safe",
        "engagement_score": 100.0,
        "content_relevance": 100.0,
        "effort_alignment": 100.0,
        "status": "recording",
        "tab_switch_count": 0,
        "copy_count": 0,
        "face_absence_count": 0,
        "forbidden_site_count": 0,
        "total_events": 0,
    }

    with _LOCAL_STORE_LOCK:
        _LOCAL_SESSIONS[session_id] = local_session

    try:
        from services.realtime import get_realtime_manager, EventType

        manager = get_realtime_manager()
        import asyncio

        asyncio.create_task(manager.broadcast_event(
            event_type=EventType.STUDENT_JOINED,
            student_id=session_data.student_id,
            session_id=session_data.exam_id,
            data={
                "id": session_id,
                "student_id": session_data.student_id,
                "student_name": session_data.student_name,
                "exam_id": session_data.exam_id,
                "status": "recording",
                "timestamp": started_at,
            }
        ))
    except Exception as ws_err:
        print(f"[WS] Failed broadcast: {ws_err}")

    return SessionResponse(
        session_id=session_id,
        exam_id=session_data.exam_id,
        student_id=session_data.student_id,
        student_name=session_data.student_name,
        started_at=started_at,
        is_active=True,
    )


def _clear_local_sessions() -> None:
    with _LOCAL_STORE_LOCK:
        _LOCAL_SESSIONS.clear()
        _LOCAL_STUDENTS.clear()


def _end_local_session(session_id: str) -> Dict[str, Any]:
    with _LOCAL_STORE_LOCK:
        session = _LOCAL_SESSIONS.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        if not session.get("is_active", True):
            return {
                "session_id": session_id,
                "status": "already_ended",
                "final_risk_score": session.get("risk_score", 0),
                "risk_level": session.get("risk_level", "safe"),
            }

        ended_at = datetime.utcnow().isoformat()
        session["is_active"] = False
        session["ended_at"] = ended_at
        session["status"] = "ended"

        return {
            "session_id": session_id,
            "status": "ended",
            "final_risk_score": session.get("risk_score", 0),
            "risk_level": session.get("risk_level", "safe"),
            "duration_seconds": 0,
        }


def _local_list_sessions(active_only: bool = False, limit: int = 100) -> List[SessionSummary]:
    with _LOCAL_STORE_LOCK:
        sessions = list(_LOCAL_SESSIONS.values())
    proctor_lookup = _build_proctor_lookup(sessions)

    if active_only:
        sessions = [session for session in sessions if session.get("is_active", True)]

    sessions = sorted(sessions, key=lambda session: session.get("started_at", ""), reverse=True)
    return [
        _build_local_summary(session, _resolve_proctor_session_id(session, proctor_lookup))
        for session in sessions[:limit]
    ]

@router.post("/create", response_model=SessionResponse)
async def create_session(session_data: SessionCreate):
    """Create a new exam session using Supabase"""
    
    try:
        # 1. Auto-create student if doesn't exist
        student_res = supabase.table("students").select("*").eq("id", session_data.student_id).execute()
        
        if not student_res.data:
            email = session_data.student_email or f"{session_data.student_id}@examguard.internal"
            supabase.table("students").insert({
                "id": session_data.student_id,
                "name": session_data.student_name,
                "email": email
            }).execute()
        
        # 2. Check if the exam_id is valid (pre-registered by a proctor)
        # We normalize both to uppercase and trim spaces to avoid common entry errors
        target_exam_id = session_data.exam_id.strip()
        print(f"[Session] Student trying to join exam_id: '{target_exam_id}' as '{session_data.student_id}'")
        
        creating_proctor = session_data.student_id.startswith("PROCTOR-")
        
        if not creating_proctor:
            # Look for ANY proctor session with this exam_id (case-insensitive)
            code_res = supabase.table("exam_sessions").select("id, exam_id")\
                .ilike("exam_id", target_exam_id)\
                .ilike("student_id", "PROCTOR-%")\
                .execute()
            
            if not code_res.data:
                # Lazy-activation: If the proctor hasn't joined yet, we still allow the student 
                # but we log it. This prevents the "Invalid exam code" error during testing.
                print(f"[Session] INFO: Student joined '{target_exam_id}' before proctor. Allowing lazy-activation.")
            else:
                # Use the canonical exam_id from the proctor session to ensure exact matching
                session_data.exam_id = code_res.data[0]["exam_id"]
                print(f"[Session] APPROVED: Student joined existing exam '{session_data.exam_id}'")

        # 3. Create new session
        session_id = str(uuid.uuid4())
        session_res = supabase.table("exam_sessions").insert({
            "id": session_id,
            "student_id": session_data.student_id,
            "exam_id": session_data.exam_id,
            "is_active": True,
            "started_at": datetime.utcnow().isoformat(),
            "risk_score": 0.0,
            "risk_level": "safe",
            "engagement_score": 100.0,
            "content_relevance": 100.0,
            "effort_alignment": 100.0,
            "status": "recording"
        }).execute()
        
        if not session_res.data:
            raise HTTPException(status_code=500, detail="Failed to create session in Supabase")
            
        new_session = session_res.data[0]
        
        # 4. Broadcast join event to dashboard via WebSocket
        try:
            from services.realtime import get_realtime_manager, EventType
            manager = get_realtime_manager()
            import asyncio
            # Broadcast to the EXAM level room (proctors join room by exam_id)
            asyncio.create_task(manager.broadcast_event(
                event_type=EventType.STUDENT_JOINED,
                student_id=session_data.student_id,
                session_id=session_data.exam_id,
                data={
                    "id": session_id,
                    "student_id": session_data.student_id,
                    "student_name": session_data.student_name,
                    "exam_id": session_data.exam_id,
                    "status": "recording",
                    "timestamp": datetime.utcnow().isoformat()
                }
            ))
        except Exception as ws_err:
            print(f"[WS] Failed broadcast: {ws_err}")
            
        return SessionResponse(
            session_id=new_session["id"],
            exam_id=new_session["exam_id"],
            student_id=new_session["student_id"],
            student_name=session_data.student_name,
            started_at=new_session["started_at"],
            is_active=True
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Session] Supabase session create failed, using local fallback: {e}")
        return _create_local_session(session_data)


@router.delete("/clear", tags=["Admin"])
async def clear_all_sessions():
    """Wipe all sessions and related data from the database (Dev/Admin only)"""
    try:
        errors = []
        
        # Delete in correct foreign key order (children first)
        tables_to_clear = [
            ("research_journey", "id", "00000000-0000-0000-0000-000000000000"),
            ("events", "id", "-1"),
            ("analysis_results", "id", "00000000-0000-0000-0000-000000000000"),
            ("exam_sessions", "id", "00000000-0000-0000-0000-000000000000"),
            ("students", "id", "-1"),
        ]
        
        for table, id_field, dummy_id in tables_to_clear:
            try:
                supabase.table(table).delete().neq(id_field, dummy_id).execute()
            except Exception as e:
                errors.append(f"{table}: {str(e)}")
        
        if errors:
            return {"status": "partial", "message": "Some tables had issues", "errors": errors}
        
        # Also clear in-memory event history so old alerts don't replay
        try:
            from services.realtime import get_realtime_manager
            mgr = get_realtime_manager()
            mgr.event_history.clear()
        except Exception:
            pass
            
        return {"status": "success", "message": "Cleared all session data successfully."}
    except Exception as e:
        print(f"[Session] Supabase clear failed, using local fallback: {e}")
        _clear_local_sessions()

        try:
            from services.realtime import get_realtime_manager
            mgr = get_realtime_manager()
            mgr.event_history.clear()
        except Exception:
            pass

        return {"status": "success", "message": "Cleared all local session data successfully."}


@router.post("/{session_id}/end")
async def end_session(session_id: str):
    """End an exam session and calculate final risk score via Supabase"""
    
    try:
        # 1. Get session
        session_res = supabase.table("exam_sessions").select("*").eq("id", session_id).execute()
        if not session_res.data:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = session_res.data[0]
        if not session["is_active"]:
            # Idempotent: return success if already ended
            return {
                "session_id": session_id,
                "status": "already_ended",
                "final_risk_score": session.get("risk_score", 0),
                "risk_level": session.get("risk_level", "safe")
            }
        
        # 2. Calculate risk score
        final_score = session.get("risk_score", 0.0)
        risk_level = session.get("risk_level", "safe")
        
        # 3. Update session
        update_res = supabase.table("exam_sessions").update({
            "is_active": False,
            "ended_at": datetime.utcnow().isoformat(),
            "status": "ended",
            "risk_score": final_score,
            "risk_level": risk_level
        }).eq("id", session_id).execute()
        
        if not update_res.data:
             raise HTTPException(status_code=500, detail="Failed to update session")
             
        updated_session = update_res.data[0]
        
        # Broadcast end event
        try:
            from services.realtime import get_realtime_manager, EventType
            manager = get_realtime_manager()
            import asyncio
            asyncio.create_task(manager.broadcast_event(
                event_type=EventType.SESSION_ENDED,
                student_id=session["student_id"],
                session_id=session["exam_id"],
                data={"id": session_id}
            ))
        except: pass

        return {
            "session_id": session_id,
            "status": "ended",
            "final_risk_score": updated_session["risk_score"],
            "risk_level": updated_session["risk_level"],
            "duration_seconds": 0 
        }
    except HTTPException:
        try:
            return _end_local_session(session_id)
        except HTTPException:
            raise
    except Exception as e:
        print(f"[Session] Supabase end failed, using local fallback: {e}")
        return _end_local_session(session_id)


@router.get("/active/count")
async def get_active_session_count():
    """Get count of active sessions from Supabase"""
    try:
        res = supabase.table("exam_sessions").select("id", count="exact").eq("is_active", True).execute()
        return {"active_count": res.count if hasattr(res, 'count') else len(res.data)}
    except Exception as e:
        print(f"[Session] Supabase count failed, using local fallback: {e}")
        with _LOCAL_STORE_LOCK:
            active_count = sum(1 for session in _LOCAL_SESSIONS.values() if session.get("is_active", True))
        return {"active_count": active_count}


@router.get("", response_model=List[SessionSummary])
async def list_sessions(active_only: bool = False, limit: int = 100):
    """List all sessions from Supabase"""
    
    try:
        query = supabase.table("exam_sessions").select("*").order("started_at", desc=True).limit(limit)
        
        if active_only:
            query = query.eq("is_active", True)
            
        res = query.execute()
        sessions = res.data
        proctor_lookup = _build_proctor_lookup(sessions)
        
        summaries = []
        for s in sessions:
            st_res = supabase.table("students").select("name").eq("id", s["student_id"]).execute()
            student_name = st_res.data[0]["name"] if st_res.data else "Unknown"
            
            summaries.append(SessionSummary(
                id=s["id"],
                student_name=student_name,
                student_id=s["student_id"],
                exam_id=s["exam_id"],
                proctor_session_id=_resolve_proctor_session_id(s, proctor_lookup),
                started_at=s["started_at"],
                ended_at=s.get("ended_at"),
                risk_score=s["risk_score"],
                risk_level=s["risk_level"],
                engagement_score=s["engagement_score"],
                content_relevance=s["content_relevance"],
                effort_alignment=s["effort_alignment"],
                status="active" if s["is_active"] else "ended",
                stats={
                    "tab_switches": s.get("tab_switch_count", 0),
                    "copy_events": s.get("copy_count", 0),
                    "face_absences": s.get("face_absence_count", 0),
                    "forbidden_sites": s.get("forbidden_site_count", 0),
                    "total": s.get("total_events", 0)
                },
            ))
        return summaries
    except Exception as e:
        print(f"[Session] Supabase list failed, using local fallback: {e}")
        return _local_list_sessions(active_only=active_only, limit=limit)


@router.post("/{session_id}/scores")
async def update_session_scores(session_id: str, payload: dict):
    """Apply browsing-derived risk/effort scores from the extension."""
    from api.endpoints.events import _apply_browsing_scores, _resolve_session, _update_local_session

    session = _resolve_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    updates: Dict[str, Any] = {
        "total_events": (session.get("total_events") or 0) + 1,
    }
    _apply_browsing_scores(updates, payload or {})

    if supabase is not None:
        try:
            supabase.table("exam_sessions").update(updates).eq("id", session_id).execute()
        except Exception as db_err:
            print(f"[Session] Supabase score update failed, using local fallback: {db_err}")
            _update_local_session(session_id, updates)
    else:
        _update_local_session(session_id, updates)

    try:
        from services.realtime import get_realtime_manager

        mgr = get_realtime_manager()
        await mgr.broadcast_to_session(
            session.get("exam_id") or session_id,
            {
                "type": "risk_score_update",
                "session_id": session_id,
                "student_id": session.get("student_id"),
                "risk_score": updates.get("risk_score"),
                "engagement_score": updates.get("engagement_score"),
                "effort_score": updates.get("engagement_score"),
                "risk_level": updates.get("risk_level"),
                "browsing": updates.get("browsing"),
            },
        )
    except Exception as ws_err:
        print(f"[Session] Score broadcast failed: {ws_err}")

    return {
        "success": True,
        "risk_score": updates.get("risk_score"),
        "engagement_score": updates.get("engagement_score"),
        "effort_alignment": updates.get("effort_alignment"),
        "risk_level": updates.get("risk_level"),
    }


@router.get("/{session_id}", response_model=SessionSummary)
async def get_session(session_id: str):
    """Get session details from Supabase"""
    
    try:
        res = supabase.table("exam_sessions").select("*").eq("id", session_id).execute()
        if not res.data:
            with _LOCAL_STORE_LOCK:
                local_session = _LOCAL_SESSIONS.get(session_id)
            if not local_session:
                raise HTTPException(status_code=404, detail="Session not found")

            with _LOCAL_STORE_LOCK:
                proctor_lookup = _build_proctor_lookup(list(_LOCAL_SESSIONS.values()))
            return _build_local_summary(local_session, _resolve_proctor_session_id(local_session, proctor_lookup))
        
        s = res.data[0]
        
        # Get student name
        st_res = supabase.table("students").select("name").eq("id", s["student_id"]).execute()
        student_name = st_res.data[0]["name"] if st_res.data else "Unknown"
        proctor_res = supabase.table("exam_sessions").select("id").eq("exam_id", s["exam_id"]).ilike("student_id", "PROCTOR-%").limit(1).execute()
        proctor_session_id = s["id"] if str(s["student_id"]).startswith("PROCTOR-") else (proctor_res.data[0]["id"] if proctor_res.data else None)
        
        return SessionSummary(
            id=s["id"],
            student_name=student_name,
            student_id=s["student_id"],
            exam_id=s["exam_id"],
            proctor_session_id=proctor_session_id,
            started_at=s["started_at"],
            ended_at=s.get("ended_at"),
            risk_score=s["risk_score"],
            risk_level=s["risk_level"],
            engagement_score=s["engagement_score"],
            content_relevance=s["content_relevance"],
            effort_alignment=s["effort_alignment"],
            status="active" if s["is_active"] else "ended",
            stats={
                "tab_switches": s.get("tab_switch_count", 0),
                "copy_events": s.get("copy_count", 0),
                "face_absences": s.get("face_absence_count", 0),
                "forbidden_sites": s.get("forbidden_site_count", 0),
                "total": s.get("total_events", 0)
            },
            browsing=s.get("browsing") or _latest_browsing_summary(session_id),
        )
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        print(f"[Session] Supabase get failed, using local fallback: {e}")
        with _LOCAL_STORE_LOCK:
            local_session = _LOCAL_SESSIONS.get(session_id)
        if not local_session:
            raise HTTPException(status_code=404, detail="Session not found")
        with _LOCAL_STORE_LOCK:
            proctor_lookup = _build_proctor_lookup(list(_LOCAL_SESSIONS.values()))
        return _build_local_summary(local_session, _resolve_proctor_session_id(local_session, proctor_lookup))
