"""Reports API."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from deps import get_current_user, get_db
from schemas.report import ReportResponse, ReportTriggerResponse
from workers.report_worker import generate_report

router = APIRouter()


@router.post("/session/{session_id}", response_model=ReportTriggerResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_report(session_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    if not db:
        raise HTTPException(status_code=503, detail="Database unavailable")

    session_res = db.table("sessions").select("id").eq("id", session_id).execute()
    if not session_res.data:
        raise HTTPException(status_code=404, detail="Session not found")

    job = generate_report.delay(session_id)
    return ReportTriggerResponse(status="queued", job_id=job.id)


@router.get("/session/{session_id}", response_model=ReportResponse)
async def get_report(session_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    if not db:
        raise HTTPException(status_code=503, detail="Database unavailable")

    res = db.table("reports").select("*").eq("session_id", session_id).order("generated_at", desc=True).limit(1).execute()
    if not res.data:
        return ReportResponse(id="", session_id=session_id, status="pending")

    report = res.data[0]
    signed_url = None
    storage_path = report.get("storage_path")
    if storage_path:
        try:
            signed = db.storage.from_("reports").create_signed_url(storage_path, 3600)
            signed_url = signed.get("signedURL") or signed.get("signed_url")
        except Exception:
            signed_url = None

    return ReportResponse(
        id=report["id"],
        session_id=session_id,
        storage_path=storage_path,
        signed_url=signed_url,
        generated_at=report.get("generated_at"),
        status="ready" if storage_path else "pending",
    )
