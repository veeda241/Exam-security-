"""
ExamGuard Pro - Gaze Tracking Module (Modern Tasks API)
"""

import numpy as np
import os
import urllib.request
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import cv2

try:
    import mediapipe as mp
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision
    MEDIAPIPE_TASKS_AVAILABLE = True
except ImportError:
    MEDIAPIPE_TASKS_AVAILABLE = False

# Path to the .task model needed for Tasks API
GAZE_MODEL_PATH = os.path.join(os.path.dirname(__file__), "face_landmarker.task")

class GazeEstimator:
    def __init__(self):
        self.landmarker = None
        if MEDIAPIPE_TASKS_AVAILABLE:
            if not os.path.exists(GAZE_MODEL_PATH):
                print("[INFO] Downloading face landmarker for gaze tracking...")
                model_url = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
                urllib.request.urlretrieve(model_url, GAZE_MODEL_PATH)

            try:
                base_options = python.BaseOptions(model_asset_path=GAZE_MODEL_PATH)
                options = vision.FaceLandmarkerOptions(
                    base_options=base_options,
                    output_face_blendshapes=True,
                    num_faces=1
                )
                self.landmarker = vision.FaceLandmarker.create_from_options(options)
            except Exception as e:
                print(f"[ERROR] Gaze landmarker init failed: {e}")

    def estimate_gaze(self, frame):
        """Estimate gaze using Tasks API result"""
        if not self.landmarker:
            return None
            
        try:
            h, w, _ = frame.shape
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            result = self.landmarker.detect(mp_image)
            
            if result.face_landmarks:
                # Use eye landmarks to estimate direction
                # Standard indices for eyes in face mesh: 
                # Left Eye Center approx: 468, Right Eye Center approx: 473 (in legacy)
                # In Tasks, landmarks are still indexed the same.
                landmarks = result.face_landmarks[0]
                
                # Check for iris/eye ratios
                # Left Iris: 468, Right Iris: 473
                re_iris = landmarks[473]
                le_iris = landmarks[468]
                
                # Center of screen is approx (0.5, 0.5)
                # Normalize to -1 to 1
                gaze_x = (re_iris.x + le_iris.x) / 2
                gaze_y = (re_iris.y + le_iris.y) / 2
                
                return {
                    "x": (gaze_x - 0.5) * 4, # Scale for sensitivity
                    "y": (gaze_y - 0.5) * 4,
                    "confidence": 0.9,
                    "timestamp": datetime.utcnow().timestamp() * 1000
                }
        except Exception:
            pass
        return None

class GazeTracker:
    def __init__(self):
        self.estimator = GazeEstimator()
        self.attention_score = 100.0

    def get_analysis(self, frame):
        gaze = self.estimator.estimate_gaze(frame)
        zone = "center"
        
        if gaze:
            if gaze['x'] < -0.3: zone = "left"
            elif gaze['x'] > 0.3: zone = "right"
            if gaze['y'] < -0.3: zone = "top_" + zone
            elif gaze['y'] > 0.3: zone = "bottom_" + zone
            
            # Simple attention decay
            if abs(gaze['x']) > 0.7 or abs(gaze['y']) > 0.7:
                 self.attention_score = max(0, self.attention_score - 5)
            else:
                 self.attention_score = min(100, self.attention_score + 2)
                 
        return {
            "current_zone": zone,
            "attention_score": self.attention_score,
            "gaze_point": gaze
        }

# Singleton
_gaze_service = None

def get_gaze_service():
    global _gaze_service
    if _gaze_service is None:
        _gaze_service = GazeTracker()
    return _gaze_service
