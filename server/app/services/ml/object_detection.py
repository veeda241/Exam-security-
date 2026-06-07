import cv2
import numpy as np
from typing import Dict, Any, List
from loguru import logger
import os

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    logger.warning("Ultralytics YOLO not installed")

class ObjectDetectionService:
    def __init__(self, model_name: str = "yolov8n.pt"):
        self.model = None
        if YOLO_AVAILABLE:
            try:
                # Use a model file if it exists, otherwise it will download
                self.model = YOLO(model_name)
                logger.info(f"YOLOv8 model {model_name} loaded")
            except Exception as e:
                logger.error(f"YOLOv8 init failed: {e}")

    def detect(self, frame: np.ndarray) -> Dict[str, Any]:
        results = {"phone_detected": False, "objects": []}
        if self.model is None or frame is None:
            return results

        try:
            # Run inference
            detections = self.model(frame, verbose=False)[0]
            
            for box in detections.boxes:
                cls_id = int(box.cls[0])
                label = detections.names[cls_id]
                conf = float(box.conf[0])
                
                if label == "cell phone" and conf > 0.5:
                    results["phone_detected"] = True
                
                results["objects"].append({
                    "label": label,
                    "confidence": conf,
                    "box": box.xyxy[0].tolist()
                })
        except Exception as e:
            logger.error(f"YOLO detection error: {e}")
            
        return results

_service = None
def get_object_service():
    global _service
    if _service is None:
        _service = ObjectDetectionService()
    return _service
