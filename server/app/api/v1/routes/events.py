"""Event ingestion API — enqueues ML jobs, writes client events directly."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from core.rate_limit import get_rate_limiter
from core.risk_engine import Event, RiskConfig, compute_risk
from deps import get_current_user, get_db
from schemas.event import CLIENT_EVENT_TYPES, ML_EVENT_TYPES, EventCreate, EventIngestResponse, EventResponse
from server.workers.utils import get_active_risk_config, insert_event, publish_session_message, recompute_and_update_session_risk

router = APIRouter()


def _enqueue_ml_job(event_type: str, session_id: str, payload: dict) -> str | None:
    frame_b64 = payload.get("frame_b64") or payload.get("image")
    text = payload.get("text") or payload.get("answer")

    if event_type == "frame_sample" and frame_b64:
        session = _get_session_monitoring_tier(session_id)
        if session == "reduced":
            return None

        from server.workers.face_worker import process_frame as face_task
        from server.workers.gaze_worker import process_frame as gaze_task
        from server.workers.object_worker import process_frame as object_task

        face_task.delay(session_id, frame_b64)
        gaze_task.delay(session_id, frame_b64)
        object_task.delay(session_id, frame_b64)
        return "face+gaze+object"

    if event_type == "screenshot" and frame_b64:
        from server.workers.ocr_worker import process_frame as ocr_task
        job = ocr_task.delay(session_id, frame_b64)
        return job.id

    if event_type == "answer_submit" and text:
        from server.workers.nlp_worker import check_similarity
        job = check_similarity.delay(session_id, text)
        return job.id

    return None


def _get_session_monitoring_tier(session_id: str) -> str:
    from supabase_client import get_supabase
    sb = get_supabase()
    if not sb:
        return "full"
    res = sb.table("sessions").select("monitoring_tier").eq("id", session_id).execute()
    if res.data:
        return res.data[0].get("monitoring_tier", "full")
    return "full"


@router.post("/", response_model=EventIngestResponse, status_code=status.HTTP_202_ACCEPTED)
async def ingest_event(
    event_in: EventCreate,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    if not db:
        raise HTTPException(status_code=503, detail="Database unavailable")

    limiter = get_rate_limiter()
    if not limiter.allow(event_in.session_id):
        raise HTTPException(status_code=429, detail="Rate limit exceeded for session")

    session_res = db.table("sessions").select("id, status, student_id").eq("id", event_in.session_id).execute()
    if not session_res.data:
        raise HTTPException(status_code=404, detail="Session not found")
    session = session_res.data[0]
    if session.get("status") != "active":
        raise HTTPException(status_code=400, detail="Session is not active")

    normalized_type = event_in.type.lower().replace("-", "_")
    job_id = None

    if normalized_type in ML_EVENT_TYPES:
        job_id = _enqueue_ml_job(normalized_type, event_in.session_id, event_in.payload)
        return EventIngestResponse(status="accepted", job_id=job_id)

    # Client-side events: write immediately and recompute risk
    config = get_active_risk_config()
    weight = float(config.weights.get(normalized_type, 0))
    event = insert_event(
        event_in.session_id,
        normalized_type,
        event_in.payload,
        weight=weight,
    )
    if event:
        publish_session_message(event_in.session_id, {
            "type": "event",
            "session_id": event_in.session_id,
            "event": event,
        })
    recompute_and_update_session_risk(event_in.session_id)

    return EventIngestResponse(
        status="accepted",
        event_id=event.get("id") if event else None,
    )


@router.get("/session/{session_id}", response_model=List[EventResponse])
async def list_session_events(
    session_id: str,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    if not db:
        raise HTTPException(status_code=503, detail="Database unavailable")

    res = db.table("v2_events").select("*").eq("session_id", session_id).order("created_at").execute()
    return [EventResponse(**row) for row in (res.data or [])]
