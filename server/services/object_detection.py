"""
ExamGuard Pro - Object Detection
YOLOv8 integration for identifying forbidden objects
"""

import os
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    print("[WARN] ultralytics not installed. Object detection disabled.")
import cv2
import numpy as np

class ObjectDetector:
    def __init__(self):
        if not YOLO_AVAILABLE:
            self.model = None
            self.FORBIDDEN_CLASSES = {}
            return
        # Load nano model for speed
        # Will auto-download on first run
        # Move weight to models/weights for organization
        weights_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models", "weights", "yolov8n.pt")
        # Ensure directory exists if we download it
        os.makedirs(os.path.dirname(weights_path), exist_ok=True)
        self.model = YOLO(weights_path)
        
        # COCO Classes of interest
        self.FORBIDDEN_CLASSES = {
            67: "cell phone",
            73: "book",
            63: "laptop"  # Contextual: second laptop?
        }
        
    def detect(self, image):
        """
        Detect forbidden objects in image
        Args:
            image: numpy array (cv2 image)
        Returns:
            dict: { detected: bool, objects: list, risk_score: int }
        """
        if self.model is None:
            return {"forbidden_detected": False, "objects": [], "risk_score": 0}
        results = self.model(image, verbose=False)
        
        detected_objects = []
        risk_score = 0
        
        for result in results:
            boxes = result.boxes
            for box in boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                
                if cls_id in self.FORBIDDEN_CLASSES and conf > 0.4:
                    obj_name = self.FORBIDDEN_CLASSES[cls_id]
                    detected_objects.append({
                        "object": obj_name,
                        "confidence": conf,
                        "box": box.xyxy[0].tolist()
                    })
                    
                    # Risk Calculation
                    if obj_name == "cell phone":
                        risk_score += 40
                    elif obj_name == "book":
                        risk_score += 30
                    elif obj_name == "laptop":
                        risk_score += 20 # Lower risk, might be false positive with main screen

        return {
            "forbidden_detected": len(detected_objects) > 0,
            "objects": detected_objects,
            "risk_score": min(100, risk_score)
        }

# Singleton
# Initialize lazily or on startup
object_detector = None

def get_object_detector():
    global object_detector
    if object_detector is None:
        object_detector = ObjectDetector()
    return object_detector
