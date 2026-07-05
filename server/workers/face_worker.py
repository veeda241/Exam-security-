"""Face detection worker — MediaPipe / Haar fallback."""
from __future__ import annotations

import base64
import io
import os
import sys

_server_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _server_dir not in sys.path:
    sys.path.insert(0, _server_dir)

import numpy as np
from PIL import Image

from workers.celery_app import celery_app
from workers.utils import finalize_worker_result


def _decode_frame(frame_b64: str) -> np.ndarray:
    raw = base64.b64decode(frame_b64.split(",")[-1])
    img = Image.open(io.BytesIO(raw)).convert("RGB")
    return np.array(img)


@celery_app.task(name="workers.face_worker.process_frame", bind=True, max_retries=2)
def process_frame(self, session_id: str, frame_b64: str, ts: str | None = None) -> dict:
    from services.face_detection import SecureVision

    vision = SecureVision()
    frame = _decode_frame(frame_b64)

    import cv2
    bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    result = vision.analyze_frame(bgr)

    violations = result.get("violations", [])
    detections = result.get("detections", [])
    face_count = len(detections)
    face_present = bool(result.get("face_detected", face_count > 0))

    if any(v in violations for v in ("MULTIPLE_FACES_DETECTED", "MULTIPLE_FACES")) or face_count > 1:
        event_type = "multiple_faces"
        payload = {"face_present": True, "count": max(face_count, 2)}
    elif any(v in violations for v in ("FACE_ABSENT_VIOLATION", "FACE_NOT_FOUND")) or not face_present:
        event_type = "face_missing"
        payload = {"face_present": False, "count": 0}
    else:
        return {"session_id": session_id, "status": "ok", "face_present": True}

    return finalize_worker_result(session_id, event_type, payload)
