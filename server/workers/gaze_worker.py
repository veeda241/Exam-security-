"""Gaze tracking worker — extends face detection gaze data."""
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


@celery_app.task(name="workers.gaze_worker.process_frame", bind=True, max_retries=2)
def process_frame(self, session_id: str, frame_b64: str, ts: str | None = None) -> dict:
    from services.face_detection import SecureVision

    vision = SecureVision()
    frame = _decode_frame(frame_b64)

    import cv2
    bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    result = vision.analyze_frame(bgr)

    gaze_direction = result.get("gaze_direction", "center")
    off_screen = bool(result.get("gaze_off_screen", False))
    off_screen_ms = int(result.get("off_screen_ms", 0))

    if not off_screen and gaze_direction in ("center", "unknown", None):
        return {
            "session_id": session_id,
            "status": "ok",
            "gaze_direction": gaze_direction,
        }

    payload = {
        "gaze_direction": gaze_direction,
        "off_screen_ms": off_screen_ms,
    }
    return finalize_worker_result(session_id, "gaze_away", payload)
