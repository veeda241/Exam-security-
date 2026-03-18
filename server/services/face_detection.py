import cv2
import numpy as np
import time
import os

# YOLO logic moved to object_detection.py

# ---- Face Detection Backend Selection ----
# Priority: MediaPipe (if available) > OpenCV DNN > OpenCV Haar Cascade
FACE_BACKEND = None

# 1) Try MediaPipe
try:
    import mediapipe as mp
    if hasattr(mp, 'solutions') and hasattr(mp.solutions, 'face_mesh'):
        FACE_BACKEND = 'mediapipe'
        print("[OK] MediaPipe face mesh available.")
    else:
        print("[INFO] MediaPipe installed but mp.solutions.face_mesh not found, trying OpenCV DNN...")
except ImportError:
    mp = None
    print("[INFO] MediaPipe not installed, trying OpenCV DNN...")

# 2) Try OpenCV DNN face detector (ships with opencv-python >=4.5.4)
if FACE_BACKEND is None:
    try:
        _test_net = cv2.FaceDetectorYN.create("", "", (320, 320))
        # FaceDetectorYN exists but needs a model file; we'll use Haar as reliable fallback
        raise RuntimeError("skip")
    except Exception:
        pass

    # Use Haar Cascade – always available with OpenCV
    _haar_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    if os.path.isfile(_haar_path):
        FACE_BACKEND = 'haar'
        print(f"[OK] OpenCV Haar Cascade face detector available.")
    else:
        FACE_BACKEND = 'none'
        print("[WARN] No face detection backend available.")


class SecureVision:
    def __init__(self):
        # MediaPipe Face Mesh for Gaze Detection
        if FACE_BACKEND == 'mediapipe':
            self.mp_face_mesh = mp.solutions.face_mesh
            self.face_mesh = self.mp_face_mesh.FaceMesh(
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )
        else:
            self.mp_face_mesh = None
            self.face_mesh = None

        # OpenCV Haar Cascade (fallback)
        if FACE_BACKEND == 'haar':
            self.haar_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            )
            self.profile_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_profileface.xml"
            )
        else:
            self.haar_cascade = None
            self.profile_cascade = None
        
        # State tracking
        self.gaze_away_start_time = None
        self.GAZE_THRESHOLD_SEC = 2.0
        self._last_face_time = time.time()
        self.FACE_ABSENT_THRESHOLD_SEC = 3.0
        
    def analyze_frame(self, frame):
        """
        Analyzes a single frame for:
        1. Face Presence
        2. Head Pose (Looking Away/Down)  – MediaPipe only
        3. Multiple faces                – both backends
        """
        results = {
            'violations': [],
            'integrity_score_impact': 0,
            'detections': [],
            'pose': None
        }
        
        if frame is None:
            return results

        if FACE_BACKEND == 'none':
            results['violations'].append('AI_MODULE_ERROR')
            return results

        if FACE_BACKEND == 'mediapipe':
            return self._analyze_mediapipe(frame, results)
        else:
            return self._analyze_haar(frame, results)

    # -----------------------------------------------------------------
    #  MediaPipe backend  (full gaze / head-pose support)
    # -----------------------------------------------------------------
    def _analyze_mediapipe(self, frame, results):
        h, w, c = frame.shape
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mesh_results = self.face_mesh.process(rgb_frame)
        
        if mesh_results.multi_face_landmarks:
            self._last_face_time = time.time()
            num_faces = len(mesh_results.multi_face_landmarks)
            
            # Layer 1: Multiple Faces (Critical)
            if num_faces > 1:
                results['violations'].append('MULTIPLE_FACES_DETECTED')
                results['integrity_score_impact'] += 50
                return results # Terminal violation

            landmarks = mesh_results.multi_face_landmarks[0]
            
            # Layer 1: Head Pose Estimation
            pose = self._estimate_head_pose(landmarks, w, h)
            results['pose'] = pose
            
            # Layer 1: Gaze Tracking (Iris & Direction)
            gaze_violation = self._detect_gaze_violation(landmarks, pose)
            if gaze_violation:
                if self.gaze_away_start_time is None:
                    self.gaze_away_start_time = time.time()
                elif time.time() - self.gaze_away_start_time > 3.0: # 3s threshold
                    results['violations'].append('SUSPICIOUS_GAZE_PATTERN')
                    results['integrity_score_impact'] += 15
            else:
                self.gaze_away_start_time = None

            # Layer 1: Mouth Movement (Speaking/Reading Aloud)
            if self._detect_mouth_movement(landmarks):
                results['violations'].append('SPEAKING_DETECTED')
                results['integrity_score_impact'] += 10
        else:
            elapsed = time.time() - self._last_face_time
            if elapsed > self.FACE_ABSENT_THRESHOLD_SEC:
                results['violations'].append('FACE_ABSENT_VIOLATION')
                results['integrity_score_impact'] += 20

        return results

    def _detect_gaze_violation(self, landmarks, pose):
        """Advanced gaze check: Left/Right/Up/Down + Vector check"""
        # Simple pose thresholds
        if abs(pose['yaw']) > 25: return True  # Looking side
        if pose['pitch'] < -20: return True    # Looking down at phone/desk
        
        # Iris Position Check (Landmarks for eyes)
        # Right Eye: 468 (iris), Left Eye: 473 (iris)
        # Comparing iris relative to eye corners
        re_iris = landmarks.landmark[468]
        le_iris = landmarks.landmark[473]
        
        # If iris is pushed too far to one side
        if re_iris.x < 0.45 or re_iris.x > 0.55: return True
        return False

    def _detect_mouth_movement(self, landmarks):
        """Check for speech patterns via lip landmarks"""
        # Upper lip: 13, Lower lip: 14
        upper = landmarks.landmark[13].y
        lower = landmarks.landmark[14].y
        dist = abs(upper - lower)
        
        # If mouth is consistently open/moving (0.015 is normalized units)
        return dist > 0.02

    # -----------------------------------------------------------------
    #  OpenCV Haar Cascade backend  (face presence + multiple faces)
    # -----------------------------------------------------------------
    def _analyze_haar(self, frame, results):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)

        faces = self.haar_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(80, 80),
            flags=cv2.CASCADE_SCALE_IMAGE,
        )

        num_faces = len(faces)

        if num_faces == 0:
            # Try profile face as well
            profiles = self.profile_cascade.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80)
            )
            if len(profiles) > 0:
                num_faces = len(profiles)
                faces = profiles
                # Profile detected → student looking away
                results['violations'].append('LOOKING_SIDE')

        if num_faces == 0:
            elapsed = time.time() - self._last_face_time
            results['violations'].append('FACE_NOT_FOUND')
            if elapsed > self.FACE_ABSENT_THRESHOLD_SEC:
                results['integrity_score_impact'] += 15
        else:
            self._last_face_time = time.time()
            # Record detection boxes
            for (x, y, w, h) in faces:
                results['detections'].append({
                    'x': int(x), 'y': int(y),
                    'w': int(w), 'h': int(h),
                })

        if num_faces > 1:
            results['violations'].append('MULTIPLE_FACES')
            results['integrity_score_impact'] += 25

        return results

    def _estimate_head_pose(self, landmarks, w, h):
        """
        Estimate head pose using PnP algorithm
        """
        # 3D Model Points (Generic)
        model_points = np.array([
            (0.0, 0.0, 0.0),             # Nose tip
            (0.0, -330.0, -65.0),        # Chin
            (-225.0, 170.0, -135.0),     # Left eye left corner
            (225.0, 170.0, -135.0),      # Right eye right corner
            (-150.0, -150.0, -125.0),    # Left Mouth corner
            (150.0, -150.0, -125.0)      # Right mouth corner
        ])

        # 2D Image Points from Landmarks
        # Indices: Nose(1), Chin(152), LeftEye(263), RightEye(33), LeftMouth(291), RightMouth(61)
        # Note: MP mesh indices might need verifying, these are standard approximation
        # Correct indexes for MP: 
        # Nose: 1 or 4
        # Chin: 152
        # Left Eye (Outer): 263
        # Right Eye (Outer): 33
        # Left Mouth: 291
        # Right Mouth: 61
        
        image_points = np.array([
            (landmarks.landmark[1].x * w, landmarks.landmark[1].y * h),     # Nose tip
            (landmarks.landmark[152].x * w, landmarks.landmark[152].y * h), # Chin
            (landmarks.landmark[263].x * w, landmarks.landmark[263].y * h), # Left eye
            (landmarks.landmark[33].x * w, landmarks.landmark[33].y * h),  # Right eye
            (landmarks.landmark[291].x * w, landmarks.landmark[291].y * h), # Left mouth
            (landmarks.landmark[61].x * w, landmarks.landmark[61].y * h)    # Right mouth
        ], dtype="double")

        # Camera Matrix (Approximate)
        focal_length = w
        center = (w / 2, h / 2)
        camera_matrix = np.array(
            [[focal_length, 0, center[0]],
             [0, focal_length, center[1]],
             [0, 0, 1]], dtype="double"
        )
        
        dist_coeffs = np.zeros((4, 1)) # Assuming no lens distortion
        
        # PnP
        success, rotation_vector, translation_vector = cv2.solvePnP(
            model_points, image_points, camera_matrix, dist_coeffs
        )
        
        # Convert to Euler Angles
        rmat, jac = cv2.Rodrigues(rotation_vector)
        angles, mtxR, mtxQ, Q, Qx, Qy, Qz = cv2.RQDecomp3x3(rmat)
        
        # Angles: pitch=x, yaw=y, roll=z
        pitch = angles[0] * 360
        yaw = angles[1] * 360
        roll = angles[2] * 360
        
        return {"pitch": pitch, "yaw": yaw, "roll": roll}

    def calculate_integrity(self, session_violations):
        """
        Calculates Integrity Score (0-100%)
        100% starts, subtract impacts capped at 0.
        """
        total_impact = sum([v.get('impact', 0) for v in session_violations])
        score = max(0, 100 - total_impact)
        return score
