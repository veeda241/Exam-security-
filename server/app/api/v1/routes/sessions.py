"""Sessions lifecycle API."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status

from deps import get_current_user, get_proctor_user, get_db
from schemas.session import SessionCreate, SessionResponse, SessionUpdate

router = APIRouter()


@router.post("/", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def start_session(
    session_in: SessionCreate,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    if not db:
        raise HTTPException(status_code=503, detail="Database unavailable")

    exam_res = db.table("exams").select("*").eq("id", session_in.exam_id).execute()
    if not exam_res.data:
        raise HTTPException(status_code=404, detail="Exam not found")

    consent = session_in.consent_metadata.model_dump()
    monitoring_tier = consent.get("monitoring_tier", "full")
    if not consent.get("biometric_consent"):
        monitoring_tier = "reduced"

    now = datetime.now(timezone.utc).isoformat()
    row = {
        "exam_id": session_in.exam_id,
        "student_id": user["id"],
        "status": "active",
        "started_at": now,
        "consent_metadata": consent,
        "monitoring_tier": monitoring_tier,
    }
    res = db.table("sessions").insert(row).execute()
    if not res.data:
        raise HTTPException(status_code=500, detail="Failed to start session")
    return SessionResponse(**res.data[0])


@router.get("/", response_model=List[SessionResponse])
async def list_sessions(
    exam_id: Optional[str] = None,
    status_filter: Optional[str] = None,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    if not db:
        raise HTTPException(status_code=503, detail="Database unavailable")

    query = db.table("sessions").select("*").order("started_at", desc=True)
    if exam_id:
        query = query.eq("exam_id", exam_id)
    if status_filter:
        query = query.eq("status", status_filter)

    if user.get("role") == "student":
        query = query.eq("student_id", user["id"])

    res = query.execute()
    return [SessionResponse(**row) for row in (res.data or [])]


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    if not db:
        raise HTTPException(status_code=503, detail="Database unavailable")

    res = db.table("sessions").select("*").eq("id", session_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Session not found")

    session = res.data[0]
    if user.get("role") == "student" and session.get("student_id") != user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    return SessionResponse(**session)


@router.patch("/{session_id}", response_model=SessionResponse)
async def update_session(
    session_id: str,
    session_in: SessionUpdate,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    if not db:
        raise HTTPException(status_code=503, detail="Database unavailable")

    res = db.table("sessions").select("*").eq("id", session_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Session not found")

    session = res.data[0]
    role = user.get("role")
    if role == "student" and session.get("student_id") != user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    updates = session_in.model_dump(exclude_unset=True)
    if updates.get("status") in ("completed", "terminated") and not updates.get("ended_at"):
        updates["ended_at"] = datetime.now(timezone.utc).isoformat()

    upd = db.table("sessions").update(updates).eq("id", session_id).execute()
    if not upd.data:
        raise HTTPException(status_code=500, detail="Update failed")

    updated = upd.data[0]

    if updates.get("status") in ("completed", "terminated"):
        from server.workers.report_worker import generate_report
        generate_report.delay(session_id)

    return SessionResponse(**updated)
