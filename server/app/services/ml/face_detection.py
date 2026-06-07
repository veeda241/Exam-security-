import cv2
import numpy as np
import time
import os
import urllib.request
from typing import Any, Dict, Optional
from loguru import logger

try:
    import mediapipe as mp
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False
    logger.warning("MediaPipe not installed, falling back to Haar cascades")

class FaceDetectionService:
    def __init__(self, model_path: str):
        self.model_path = model_path
        self.landmarker = None
        self.haar_cascade = None
        self._last_face_time = time.time()
        self.FACE_ABSENT_THRESHOLD_SEC = 3.0
        self._initialize()

    def _initialize(self):
        if MEDIAPIPE_AVAILABLE and os.path.exists(self.model_path):
            try:
                base_options = python.BaseOptions(model_asset_path=self.model_path)
                options = vision.FaceLandmarkerOptions(
                    base_options=base_options,
                    output_face_blendshapes=True,
                    num_faces=2
                )
                self.landmarker = vision.FaceLandmarker.create_from_options(options)
                logger.info("MediaPipe FaceLandmarker initialized")
            except Exception as e:
                logger.error(f"MediaPipe init failed: {e}")
        
        if not self.landmarker:
            try:
                self.haar_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
                logger.info("Haar cascade fallback initialized")
            except Exception as e:
                logger.warning(f"Haar cascade init failed: {e}")

    def analyze_frame(self, frame: np.ndarray) -> Dict[str, Any]:
        results = {'violations': [], 'detections': [], 'face_detected': False}
        if frame is None:
            return results

        if self.landmarker:
            return self._analyze_mediapipe(frame, results)
        elif self.haar_cascade:
            return self._analyze_haar(frame, results)
        return results

    def _analyze_mediapipe(self, frame, results):
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        detection_result = self.landmarker.detect(mp_image)
        
        if detection_result.face_landmarks:
            self._last_face_time = time.time()
            results['face_detected'] = True
            if len(detection_result.face_landmarks) > 1:
                results['violations'].append('MULTIPLE_FACES_DETECTED')
            
            for face_landmarks in detection_result.face_landmarks:
                x_coords = [lm.x for lm in face_landmarks]
                y_coords = [lm.y for lm in face_landmarks]
                h, w, _ = frame.shape
                results['detections'].append({
                    'x': int(min(x_coords) * w),
                    'y': int(min(y_coords) * h),
                    'w': int((max(x_coords) - min(x_coords)) * w),
                    'h': int((max(y_coords) - min(y_coords)) * h)
                })
        else:
            if time.time() - self._last_face_time > self.FACE_ABSENT_THRESHOLD_SEC:
                results['violations'].append('FACE_ABSENT_VIOLATION')
        
        return results

    def _analyze_haar(self, frame, results):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.haar_cascade.detectMultiScale(gray, 1.1, 8)
        if len(faces) > 0:
            self._last_face_time = time.time()
            results['face_detected'] = True
            for (x, y, w, h) in faces:
                results['detections'].append({'x': int(x), 'y': int(y), 'w': int(w), 'h': int(h)})
            if len(faces) > 1:
                results['violations'].append('MULTIPLE_FACES')
        else:
            if time.time() - self._last_face_time > self.FACE_ABSENT_THRESHOLD_SEC:
                results['violations'].append('FACE_NOT_FOUND')
        return results

_service = None
def get_face_service():
    global _service
    if _service is None:
        model_path = os.path.join(os.path.dirname(__file__), "face_landmarker.task")
        _service = FaceDetectionService(model_path)
    return _service
