"""OCR worker — Tesseract forbidden content detection."""
from __future__ import annotations

import base64
import io
import os
import sys
import tempfile

_server_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _server_dir not in sys.path:
    sys.path.insert(0, _server_dir)

from PIL import Image

from workers.celery_app import celery_app
from workers.utils import finalize_worker_result


@celery_app.task(name="workers.ocr_worker.process_frame", bind=True, max_retries=2)
def process_frame(self, session_id: str, frame_b64: str, ts: str | None = None) -> dict:
    from services.ocr import ScreenOCR

    raw = base64.b64decode(frame_b64.split(",")[-1])
    img = Image.open(io.BytesIO(raw))

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        img.save(tmp.name)
        path = tmp.name

    try:
        ocr = ScreenOCR()
        result = ocr.analyze(path)
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass

    flagged = result.get("found_keywords") or result.get("flagged_terms") or []
    if not flagged and not result.get("is_suspicious"):
        return {"session_id": session_id, "status": "ok"}

    payload = {
        "flagged_terms": flagged,
        "confidence": float(result.get("confidence", result.get("ocr_confidence", 0))),
        "text_preview": (result.get("text") or "")[:200],
    }
    return finalize_worker_result(session_id, "ocr_flag", payload)


@celery_app.task(name="workers.ocr_worker.process_text", bind=True, max_retries=2)
def process_text(self, session_id: str, text: str) -> dict:
    from services.ocr import ScreenOCR

    ocr = ScreenOCR()
    result = ocr.analyze_text(text) if hasattr(ocr, "analyze_text") else {"found_keywords": []}

    flagged = result.get("found_keywords") or []
    if not flagged:
        return {"session_id": session_id, "status": "ok"}

    payload = {"flagged_terms": flagged, "confidence": 1.0}
    return finalize_worker_result(session_id, "ocr_flag", payload)
