import asyncio
import cv2
import numpy as np
import time
import os
import urllib.request
from typing import Any, Dict

# ---- Face Detection Backend Detection (Modern Tasks API) ----
FACE_BACKEND = 'haar'
FACE_LANDMARKER_PATH = os.path.join(os.path.dirname(__file__), "face_landmarker.task")

try:
    import mediapipe as mp
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision
    
    # Download model if missing (essential for Tasks API)
    if not os.path.exists(FACE_LANDMARKER_PATH):
        print("[INFO] Downloading MediaPipe Face Landmarker task model...")
        model_url = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
        urllib.request.urlretrieve(model_url, FACE_LANDMARKER_PATH)
        
    FACE_BACKEND = 'mediapipe_tasks'
    print("[OK] MediaPipe Tasks API available.")
except Exception as e:
    print(f"[INFO] MediaPipe Tasks failed: {e}. Falling back to Haar.")

class SecureVision:
    def __init__(self):
        self.landmarker = None
        self.haar_cascade = None
        self.profile_cascade = None
        
        if FACE_BACKEND == 'mediapipe_tasks':
            try:
                base_options = python.BaseOptions(model_asset_path=FACE_LANDMARKER_PATH)
                options = vision.FaceLandmarkerOptions(
                    base_options=base_options,
                    output_face_blendshapes=True,
                    num_faces=2
                )
                self.landmarker = vision.FaceLandmarker.create_from_options(options)
                print("[OK] FaceLandmarker initialized successfully")
            except Exception as e:
                print(f"[ERROR] FaceLandmarker init failed: {e}")
                self.landmarker = None
        

        # Only try Haar if MediaPipe failed and cv2 has the data
        if not self.landmarker:
            try:
                if hasattr(cv2, 'data') and hasattr(cv2.data, 'haarcascades'):
                    self.haar_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
                    self.profile_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_profileface.xml")
                    print("[OK] Haar cascade fallback initialized")
                else:
                    print("[WARN] No face detection backend available - cv2 headless has no Haar cascades")
            except Exception as e:
                print(f"[WARN] Haar cascade init failed: {e}")

        self.gaze_away_start_time = None
        self._last_face_time = time.time()
        self.FACE_ABSENT_THRESHOLD_SEC = 3.0

    def _finalize_results(self, results: Dict[str, Any], face_detected: bool | None = None) -> Dict[str, Any]:
        normalized = dict(results)
        violations = normalized.get("violations", [])
        if not isinstance(violations, list):
            violations = [str(violations)] if violations else []

        normalized["violations"] = violations

        if face_detected is None:
            face_detected = not any(
                violation in {"FACE_NOT_FOUND", "FACE_ABSENT_VIOLATION"}
                for violation in violations
            )

        normalized["face_detected"] = face_detected
        normalized["confidence"] = 0.0 if not face_detected else (
            0.5 if any(
                violation in {"MULTIPLE_FACES_DETECTED", "MULTIPLE_FACES"}
                for violation in violations
            ) else 0.9
        )
        normalized["risk_score"] = normalized.get("integrity_score_impact", 0)
        return normalized

    def analyze_frame(self, frame, student_id: str | None = None, **_: Any):
        results = {'violations': [], 'integrity_score_impact': 0, 'detections': [], 'pose': None}
        if frame is None:
            return self._finalize_results(results, face_detected=False)

        if self.landmarker:
            return self._finalize_results(self._analyze_tasks(frame, results))
        elif self.haar_cascade is not None:
            return self._finalize_results(self._analyze_haar(frame, results))
        else:
            # No face detection available - return empty results
            return self._finalize_results(results, face_detected=False)

    def _analyze_tasks(self, frame, results):
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        detection_result = self.landmarker.detect(mp_image)
        
        if detection_result.face_landmarks:
            self._last_face_time = time.time()
            if len(detection_result.face_landmarks) > 1:
                results['violations'].append('MULTIPLE_FACES_DETECTED')
                results['integrity_score_impact'] += 50
            
            for face_landmarks in detection_result.face_landmarks:
                # Get bounding box for detection
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
            elapsed = time.time() - self._last_face_time
            if elapsed > self.FACE_ABSENT_THRESHOLD_SEC:
                results['violations'].append('FACE_ABSENT_VIOLATION')
                results['integrity_score_impact'] += 20
        
        return results


_VISION_ENGINE = SecureVision()


async def detect_face(file_path: str) -> Dict[str, Any]:
    frame = await asyncio.to_thread(cv2.imread, file_path)
    return await asyncio.to_thread(_VISION_ENGINE.analyze_frame, frame)

    def _analyze_haar(self, frame, results):
        gray = cv2.equalizeHist(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
        faces = self.haar_cascade.detectMultiScale(gray, 1.1, 8, minSize=(80, 80))
        
        if len(faces) == 0:
            profiles = self.profile_cascade.detectMultiScale(gray, 1.1, 8, minSize=(80, 80))
            if len(profiles) > 0:
                results['violations'].append('LOOKING_SIDE')
                faces = profiles

        if len(faces) == 0:
            if time.time() - self._last_face_time > self.FACE_ABSENT_THRESHOLD_SEC:
                results['violations'].append('FACE_NOT_FOUND')
        else:
            self._last_face_time = time.time()
            for (x, y, w, h) in faces:
                results['detections'].append({'x': int(x), 'y': int(y), 'w': int(w), 'h': int(h)})
            if len(faces) > 1:
                results['violations'].append('MULTIPLE_FACES')

        return results
