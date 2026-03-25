from fastapi import APIRouter, HTTPException
from supabase_client import get_supabase
from datetime import datetime
from typing import List
import uuid

from api.schemas import SessionCreate, SessionResponse, SessionSummary

router = APIRouter()
supabase = get_supabase()

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
                print(f"[Session] DENIED: No proctor session found for exam_id '{target_exam_id}'")
                raise HTTPException(status_code=400, detail=f"Invalid exam code '{target_exam_id}'. This exam has not been started by a proctor yet.")
            
            # Use the canonical exam_id from the proctor session to ensure exact matching
            session_data.exam_id = code_res.data[0]["exam_id"]
            print(f"[Session] APPROVED: Student joined exam '{session_data.exam_id}'")

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
        
        return SessionResponse(
            session_id=new_session["id"],
            student_id=new_session["student_id"],
            student_name=session_data.student_name,
            exam_id=new_session["exam_id"],
            started_at=new_session["started_at"],
            is_active=True,
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error creating session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
        raise HTTPException(status_code=500, detail=f"Failed to clear sessions: {str(e)}")


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
            raise HTTPException(status_code=400, detail="Session already ended")
        
        # 2. Calculate risk score (Note: this function needs refactoring to use Supabase)
        # For now, we'll use a placeholder or the refactored function if ready
        # from scoring.calculator import calculate_risk_score_v2
        # final_score, risk_level = await calculate_risk_score_v2(session_id)
        
        final_score = session.get("risk_score", 0.0)
        risk_level = session.get("risk_level", "safe")
        
        # 3. Update session
        update_res = supabase.table("exam_sessions").update({
            "is_active": False,
            "ended_at": datetime.utcnow().isoformat(),
            "risk_score": final_score,
            "risk_level": risk_level
        }).eq("id", session_id).execute()
        
        if not update_res.data:
             raise HTTPException(status_code=500, detail="Failed to update session")
             
        updated_session = update_res.data[0]
        
        return {
            "session_id": session_id,
            "status": "ended",
            "final_risk_score": updated_session["risk_score"],
            "risk_level": updated_session["risk_level"],
            "duration_seconds": 0 # Logic to calculate duration if needed
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}", response_model=SessionSummary)
async def get_session(session_id: str):
    """Get session details from Supabase"""
    
    try:
        res = supabase.table("exam_sessions").select("*").eq("id", session_id).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Session not found")
        
        s = res.data[0]
        
        # Get student name
        st_res = supabase.table("students").select("name").eq("id", s["student_id"]).execute()
        student_name = st_res.data[0]["name"] if st_res.data else "Unknown"
        
        return SessionSummary(
            id=s["id"],
            student_name=student_name,
            student_id=s["student_id"],
            exam_id=s["exam_id"],
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
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[SessionSummary])
async def list_sessions(active_only: bool = False, limit: int = 100):
    """List all sessions from Supabase"""
    
    try:
        query = supabase.table("exam_sessions").select("*").order("started_at", desc=True).limit(limit)
        
        if active_only:
            query = query.eq("is_active", True)
            
        res = query.execute()
        sessions = res.data
        
        summaries = []
        for s in sessions:
            st_res = supabase.table("students").select("name").eq("id", s["student_id"]).execute()
            student_name = st_res.data[0]["name"] if st_res.data else "Unknown"
            
            summaries.append(SessionSummary(
                id=s["id"],
                student_name=student_name,
                student_id=s["student_id"],
                exam_id=s["exam_id"],
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
                }
            ))
        return summaries
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/active/count")
async def get_active_session_count():
    """Get count of active sessions from Supabase"""
    try:
        res = supabase.table("exam_sessions").select("id", count="exact").eq("is_active", True).execute()
        return {"active_count": res.count if hasattr(res, 'count') else len(res.data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
