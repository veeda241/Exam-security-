"""Telemetry image upload and latest-frame endpoints."""
from __future__ import annotations

import base64
import binascii
import re
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from config import settings
from deps import get_current_user, get_db
from workers.utils import publish_session_message

router = APIRouter()
analysis_router = APIRouter()
_DATA_URL_RE = re.compile(r"^data:image/(?P<format>[a-zA-Z0-9.+-]+);base64,(?P<data>.+)$")
_EXTENSIONS = {"jpeg": ".jpg", "jpg": ".jpg", "png": ".png", "webp": ".webp"}


class ImageUpload(BaseModel):
    session_id: str
    timestamp: int | None = None
    image_data: str = Field(min_length=16)


class AnalysisUpload(BaseModel):
    session_id: str
    timestamp: int | None = None
    screen_image: str | None = None
    webcam_image: str | None = None
    is_dom_capture: bool = False
    source_url: str | None = None


def _save_image(upload: ImageUpload, kind: str) -> Path:
    match = _DATA_URL_RE.match(upload.image_data)
    if not match:
        raise HTTPException(status_code=415, detail="image_data must be a base64 data URL")
    try:
        content = base64.b64decode(match.group("data"), validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Invalid base64 image data") from exc
    if not content:
        raise HTTPException(status_code=422, detail="Image payload is empty")

    directory = settings.SCREENSHOTS_DIR if kind == "screenshot" else settings.WEBCAM_DIR
    directory.mkdir(parents=True, exist_ok=True)
    extension = _EXTENSIONS.get(match.group("format").lower(), ".bin")
    path = directory / f"{upload.session_id}-{uuid.uuid4().hex}{extension}"
    path.write_bytes(content)
    return path


async def _store_and_publish(upload: ImageUpload, kind: str) -> dict:
    path = _save_image(upload, kind)
    publish_session_message(upload.session_id, {
        "type": "telemetry_frame",
        "session_id": upload.session_id,
        "kind": kind,
        "path": path.name,
    })
    return {"status": "accepted", "session_id": upload.session_id, "filename": path.name}


@router.post("/screenshot")
async def upload_screenshot(upload: ImageUpload, user=Depends(get_current_user)):
    return await _store_and_publish(upload, "screenshot")


@router.post("/webcam")
async def upload_webcam(upload: ImageUpload, user=Depends(get_current_user)):
    return await _store_and_publish(upload, "webcam")


@analysis_router.post("/process")
async def process_analysis(upload: AnalysisUpload, user=Depends(get_current_user)):
    """Accept the extension's legacy combined capture payload.

    Storage and inference are deliberately separate: the upload is acknowledged
    immediately while the existing Celery event pipeline handles analysis.
    """
    accepted: list[str] = []
    if upload.screen_image:
        await _store_and_publish(
            ImageUpload(session_id=upload.session_id, timestamp=upload.timestamp, image_data=upload.screen_image),
            "screenshot",
        )
        accepted.append("screenshot")
    if upload.webcam_image:
        await _store_and_publish(
            ImageUpload(session_id=upload.session_id, timestamp=upload.timestamp, image_data=upload.webcam_image),
            "webcam",
        )
        accepted.append("webcam")
    return {
        "status": "accepted",
        "session_id": upload.session_id,
        "accepted": accepted,
        "face_detected": None,
        "phone_detected": None,
    }


@router.get("/latest/{session_id}")
async def latest_frame(
    session_id: str,
    type: str = "screenshot",
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    if type not in {"screenshot", "webcam"}:
        raise HTTPException(status_code=400, detail="type must be screenshot or webcam")
    if db:
        session = db.table("sessions").select("id, student_id").eq("id", session_id).execute()
        if not session.data:
            raise HTTPException(status_code=404, detail="Session not found")
        if user.get("role") == "student" and session.data[0].get("student_id") != user["id"]:
            raise HTTPException(status_code=403, detail="Access denied")

    directory = settings.SCREENSHOTS_DIR if type == "screenshot" else settings.WEBCAM_DIR
    candidates = sorted(
        (path for path in directory.glob(f"{session_id}-*") if path.is_file()),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise HTTPException(status_code=404, detail="No telemetry frame available")
    return FileResponse(candidates[0])
