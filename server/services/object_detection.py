"""
ExamGuard Pro - Object Detection (V11)
Real-time high-fidelity detection for cheating devices
"""

import os
import time
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
import cv2
import numpy as np

class ObjectDetector:
    def __init__(self):
        if not YOLO_AVAILABLE:
            self.model = None
            self.FORBIDDEN_CLASSES = {}
            return

        # Upgrading to Yolo11s for state-of-the-art accuracy on small objects
        weights_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models", "weights", "yolo11s.pt")
        os.makedirs(os.path.dirname(weights_path), exist_ok=True)
        self.model = YOLO(weights_path)
        
        # COCO Class mapping
        self.FORBIDDEN_CLASSES = {
            67: "cell phone",
            73: "book",
            63: "laptop",
            76: "watch",
            65: "remote",
            0: "person",
            62: "tv",
            64: "mouse",     # Often misclassified as gadgets
            66: "keyboard",
        }
        self._last_process_time = 0
        self._cache = None
        
    def _enhance_frame(self, image):
        # Apply Histogram Equalization / CLAHE to see better in low-light webcams
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        cl = clahe.apply(l)
        limg = cv2.merge((cl,a,b))
        return cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)

    def _apply_clahe(self, image):
        """Apply Contrast Limited Adaptive Histogram Equalization for better low-light visibility"""
        try:
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
            cl = clahe.apply(l)
            limg = cv2.merge((cl,a,b))
            return cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
        except Exception as e:
            print(f"[ObjectDetector] CLAHE failed: {e}")
            return image

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
        
        # Throttle processing to 10 FPS for stability in Streamlit
        if time.time() - self._last_process_time < 0.1:
            if self._cache: return self._cache
            
        # Pre-process for better low-light detection
        enhanced = self._apply_clahe(image)
        
        # Run detection with lower base confidence and multi-scale test (if needed)
        # Using conf=0.1 to catch faint objects but filtering in loop
        results = self.model(enhanced, conf=0.15, iou=0.45, verbose=False)
        
        detected_objects = []
        risk_score = 0
        person_count = 0
        
        for result in results:
            boxes = result.boxes
            for box in boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                
                # Check for person count separately
                if cls_id == 0:
                    person_count += 1
                    continue

                if cls_id in self.FORBIDDEN_CLASSES:
                    obj_name = self.FORBIDDEN_CLASSES[cls_id]
                    
                    # Increased sensitivity for phones/watches
                    min_conf = 0.18 if obj_name in ["cell phone", "watch"] else 0.25
                    
                    if conf > min_conf:
                        detected_objects.append({
                            "object": obj_name,
                            "confidence": conf,
                            "box": [int(x) for x in box.xyxy[0].tolist()]
                        })
                        
                        # Aggressive Risk Scoring
                        if obj_name == "cell phone": risk_score += 80
                        elif obj_name == "watch": risk_score += 50
                        elif obj_name == "book": risk_score += 40
                        else: risk_score += 20

        # Multi-person detection
        if person_count > 1:
            detected_objects.append({
                "object": f"MULTIPLE PEOPLE ({person_count})",
                "confidence": 1.0,
                "box": [0,0,0,0]
            })
            risk_score += 70

        self._cache = {
            "forbidden_detected": len([o for o in detected_objects if o["object"] != "person"]) > 0,
            "objects": detected_objects,
            "risk_score": min(100, risk_score),
            "person_count": person_count
        }
        self._last_process_time = time.time()
        return self._cache

# Singleton
object_detector = None

def get_object_detector():
    global object_detector
    if object_detector is None:
        object_detector = ObjectDetector()
    return object_detector
