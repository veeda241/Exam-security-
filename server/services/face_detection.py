import cv2
import numpy as np
import time

# YOLO logic moved to object_detection.py

# Try to import MediaPipe
try:
    import mediapipe as mp
    # Verify solutions module is accessible
    if hasattr(mp, 'solutions') and hasattr(mp.solutions, 'face_mesh'):
        MP_AVAILABLE = True
    else:
        MP_AVAILABLE = False
        print("[WARN] MediaPipe solutions not available. Face mesh disabled.")
except ImportError:
    mp = None
    MP_AVAILABLE = False
    print("[WARN] MediaPipe not installed. Face tracking disabled.")

class SecureVision:
    def __init__(self):
        # MediaPipe Face Mesh for Gaze Detection
        if MP_AVAILABLE:
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
        
        # State tracking
        self.gaze_away_start_time = None
        self.GAZE_THRESHOLD_SEC = 2.0
        
    def analyze_frame(self, frame):
        """
        Analyzes a single frame for:
        1. Face Presence
        2. Head Pose (Looking Away/Down)
        """
        results = {
            'violations': [],
            'integrity_score_impact': 0,
            'detections': [],
            'pose': None
        }
        
        if frame is None or not MP_AVAILABLE:
            if not MP_AVAILABLE:
                results['violations'].append('AI_MODULE_ERROR')
            return results

        h, w, c = frame.shape
        
        # Gaze Tracking (MediaPipe)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mesh_results = self.face_mesh.process(rgb_frame)
        
        if mesh_results.multi_face_landmarks:
            landmarks = mesh_results.multi_face_landmarks[0]
            
            # Head Pose Estimation
            pose = self._estimate_head_pose(landmarks, w, h)
            results['pose'] = pose
            
            is_looking_away = False
            
            # Check Pitch (Looking Down/Up)
            if pose['pitch'] < -15: # Looking down
                results['violations'].append('LOOKING_DOWN')
                is_looking_away = True
            elif pose['pitch'] > 20: # Looking up
                 pass # Less severe?
                 
            # Check Yaw (Looking Side)
            if abs(pose['yaw']) > 20:
                results['violations'].append('LOOKING_SIDE')
                is_looking_away = True
            
            if is_looking_away:
                if self.gaze_away_start_time is None:
                    self.gaze_away_start_time = time.time()
                elif time.time() - self.gaze_away_start_time > self.GAZE_THRESHOLD_SEC:
                    results['violations'].append('GAZE_AWAY_LONG')
                    results['integrity_score_impact'] += 20
            else:
                self.gaze_away_start_time = None
        else:
            # Face not detected
            results['violations'].append('FACE_NOT_FOUND')
            results['integrity_score_impact'] += 15

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
