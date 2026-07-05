"""Object detection worker — YOLOv8n."""
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

FLAGGED_CLASSES = {"cell phone", "phone", "laptop", "book", "tablet"}


def _decode_frame(frame_b64: str) -> np.ndarray:
    raw = base64.b64decode(frame_b64.split(",")[-1])
    img = Image.open(io.BytesIO(raw)).convert("RGB")
    return np.array(img)


@celery_app.task(name="workers.object_worker.process_frame", bind=True, max_retries=2)
def process_frame(self, session_id: str, frame_b64: str, ts: str | None = None) -> dict:
    from services.object_detection import ObjectDetector

    detector = ObjectDetector()
    frame = _decode_frame(frame_b64)

    import cv2
    bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    detections_raw = detector.detect(bgr)
    objects = detections_raw.get("objects", []) if isinstance(detections_raw, dict) else []

    flagged = [
        {"label": o.get("object", ""), "confidence": o.get("confidence", 0), "bbox": o.get("box")}
        for o in objects
        if str(o.get("object", "")).lower() in FLAGGED_CLASSES
        or "phone" in str(o.get("object", "")).lower()
        or "MULTIPLE PEOPLE" in str(o.get("object", ""))
    ]

    if not flagged and not detections_raw.get("forbidden_detected"):
        return {"session_id": session_id, "status": "ok", "detections": len(objects)}

    payload = {
        "detections": flagged,
        "count": len(flagged),
    }
    return finalize_worker_result(session_id, "object_flag", payload)
