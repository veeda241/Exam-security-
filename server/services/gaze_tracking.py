"""
ExamGuard Pro - Gaze Tracking Module
Eye movement analysis using MediaPipe FaceMesh landmarks.

100% LOCAL - No external APIs required
Uses MediaPipe which runs entirely on-device.
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from collections import deque
import math

try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False
    print("[WARN] MediaPipe not available. Gaze tracking disabled.")


# =============================================================================
# Eye Landmark Indices (MediaPipe FaceMesh)
# =============================================================================

# Left eye landmarks
LEFT_EYE = [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398]
LEFT_IRIS = [474, 475, 476, 477]  # Iris landmarks (if available)
LEFT_EYE_CENTER = 468  # Approximate center

# Right eye landmarks  
RIGHT_EYE = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
RIGHT_IRIS = [469, 470, 471, 472]
RIGHT_EYE_CENTER = 473

# Eye corners for gaze direction
LEFT_EYE_INNER = 362
LEFT_EYE_OUTER = 263
RIGHT_EYE_INNER = 133
RIGHT_EYE_OUTER = 33


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class GazePoint:
    """Single gaze measurement"""
    timestamp: float
    x: float  # Normalized horizontal position (-1 to 1, left to right)
    y: float  # Normalized vertical position (-1 to 1, up to down)
    confidence: float = 1.0
    left_eye_ratio: float = 0.0
    right_eye_ratio: float = 0.0
    

@dataclass
class GazeZone:
    """Screen zone for attention analysis"""
    name: str
    x_min: float
    x_max: float
    y_min: float
    y_max: float
    

@dataclass
class GazeHeatmapCell:
    """Single cell in attention heatmap"""
    row: int
    col: int
    duration_ms: float = 0.0
    visit_count: int = 0


@dataclass  
class GazeAnalysis:
    """Complete gaze analysis result"""
    student_id: str
    timestamp: str
    
    # Current gaze
    current_gaze_x: float = 0.0
    current_gaze_y: float = 0.0
    looking_at_screen: bool = True
    
    # Attention metrics
    attention_score: float = 100.0  # 0-100
    focus_duration_ms: float = 0.0
    distraction_count: int = 0
    
    # Suspicious indicators
    looking_away_duration_ms: float = 0.0
    rapid_eye_movement_count: int = 0
    reading_pattern_detected: bool = False
    
    # Zones
    time_in_zones: Dict[str, float] = field(default_factory=dict)
    current_zone: str = "center"
    
    # Anomalies
    anomaly_score: float = 0.0
    anomalies: List[str] = field(default_factory=list)


# =============================================================================
# Gaze Estimator
# =============================================================================

class GazeEstimator:
    """
    Estimates gaze direction from facial landmarks.
    Uses iris position relative to eye corners.
    """
    
    def __init__(self):
        self.calibration_points: List[Tuple[float, float]] = []
        self.is_calibrated = False
        
    def estimate_gaze(self, landmarks: List, image_width: int, image_height: int) -> Optional[GazePoint]:
        """
        Estimate gaze point from facial landmarks.
        
        Args:
            landmarks: MediaPipe face landmarks
            image_width: Width of input image
            image_height: Height of input image
            
        Returns:
            GazePoint with normalized coordinates
        """
        if not landmarks:
            return None
            
        try:
            # Get eye landmarks
            left_eye_inner = self._get_landmark(landmarks, LEFT_EYE_INNER)
            left_eye_outer = self._get_landmark(landmarks, LEFT_EYE_OUTER)
            right_eye_inner = self._get_landmark(landmarks, RIGHT_EYE_INNER)
            right_eye_outer = self._get_landmark(landmarks, RIGHT_EYE_OUTER)
            
            # Get iris centers (if available) or estimate from eye center
            left_iris = self._get_iris_center(landmarks, LEFT_IRIS, LEFT_EYE)
            right_iris = self._get_iris_center(landmarks, RIGHT_IRIS, RIGHT_EYE)
            
            # Calculate horizontal gaze ratio for each eye
            left_ratio = self._calculate_gaze_ratio(
                left_iris, left_eye_inner, left_eye_outer
            )
            right_ratio = self._calculate_gaze_ratio(
                right_iris, right_eye_inner, right_eye_outer
            )
            
            # Average both eyes
            horizontal_ratio = (left_ratio + right_ratio) / 2
            
            # Calculate vertical gaze (using eye aspect ratio changes)
            vertical_ratio = self._calculate_vertical_gaze(landmarks)
            
            # Convert to normalized coordinates
            gaze_x = (horizontal_ratio - 0.5) * 2  # -1 to 1
            gaze_y = (vertical_ratio - 0.5) * 2    # -1 to 1
            
            return GazePoint(
                timestamp=datetime.utcnow().timestamp() * 1000,
                x=gaze_x,
                y=gaze_y,
                confidence=0.8,
                left_eye_ratio=left_ratio,
                right_eye_ratio=right_ratio
            )
            
        except Exception as e:
            print(f"[GazeEstimator] Error: {e}")
            return None
    
    def _get_landmark(self, landmarks, index: int) -> Tuple[float, float]:
        """Get landmark coordinates"""
        lm = landmarks[index]
        return (lm.x, lm.y)
    
    def _get_iris_center(self, landmarks, iris_indices: List[int], 
                         eye_indices: List[int]) -> Tuple[float, float]:
        """Get iris center or estimate from eye landmarks"""
        try:
            # Try to use iris landmarks first
            if iris_indices:
                xs = [landmarks[i].x for i in iris_indices]
                ys = [landmarks[i].y for i in iris_indices]
                return (np.mean(xs), np.mean(ys))
        except:
            pass
            
        # Fall back to eye center estimation
        xs = [landmarks[i].x for i in eye_indices]
        ys = [landmarks[i].y for i in eye_indices]
        return (np.mean(xs), np.mean(ys))
    
    def _calculate_gaze_ratio(self, iris: Tuple[float, float],
                               inner: Tuple[float, float],
                               outer: Tuple[float, float]) -> float:
        """
        Calculate horizontal gaze ratio.
        0 = looking right, 0.5 = center, 1 = looking left
        """
        eye_width = abs(outer[0] - inner[0])
        if eye_width == 0:
            return 0.5
            
        # Distance from inner corner to iris
        iris_distance = abs(iris[0] - inner[0])
        
        ratio = iris_distance / eye_width
        return np.clip(ratio, 0, 1)
    
    def _calculate_vertical_gaze(self, landmarks) -> float:
        """
        Estimate vertical gaze direction.
        Uses eye openness and head tilt as proxies.
        """
        try:
            # Calculate eye aspect ratios
            left_ear = self._eye_aspect_ratio(landmarks, LEFT_EYE)
            right_ear = self._eye_aspect_ratio(landmarks, RIGHT_EYE)
            
            avg_ear = (left_ear + right_ear) / 2
            
            # Normalize to 0-1 range (typical EAR range is 0.1-0.4)
            vertical = np.clip((avg_ear - 0.1) / 0.3, 0, 1)
            
            return vertical
            
        except:
            return 0.5
    
    def _eye_aspect_ratio(self, landmarks, eye_indices: List[int]) -> float:
        """Calculate eye aspect ratio (EAR)"""
        try:
            # Get vertical distances
            p2 = landmarks[eye_indices[1]]
            p6 = landmarks[eye_indices[5]]
            p3 = landmarks[eye_indices[2]]
            p5 = landmarks[eye_indices[4]]
            p1 = landmarks[eye_indices[0]]
            p4 = landmarks[eye_indices[3]]
            
            v1 = math.sqrt((p2.x - p6.x)**2 + (p2.y - p6.y)**2)
            v2 = math.sqrt((p3.x - p5.x)**2 + (p3.y - p5.y)**2)
            h = math.sqrt((p1.x - p4.x)**2 + (p1.y - p4.y)**2)
            
            if h == 0:
                return 0.3
                
            ear = (v1 + v2) / (2.0 * h)
            return ear
            
        except:
            return 0.3


# =============================================================================
# Gaze Tracker
# =============================================================================

class GazeTracker:
    """
    Tracks gaze over time and detects patterns/anomalies.
    """
    
    def __init__(self, history_size: int = 300):
        self.estimator = GazeEstimator()
        self.history: deque = deque(maxlen=history_size)
        
        # Screen zones for attention analysis
        self.zones = [
            GazeZone("top_left", -1, -0.33, -1, -0.33),
            GazeZone("top_center", -0.33, 0.33, -1, -0.33),
            GazeZone("top_right", 0.33, 1, -1, -0.33),
            GazeZone("center_left", -1, -0.33, -0.33, 0.33),
            GazeZone("center", -0.33, 0.33, -0.33, 0.33),
            GazeZone("center_right", 0.33, 1, -0.33, 0.33),
            GazeZone("bottom_left", -1, -0.33, 0.33, 1),
            GazeZone("bottom_center", -0.33, 0.33, 0.33, 1),
            GazeZone("bottom_right", 0.33, 1, 0.33, 1),
            GazeZone("off_screen", -2, 2, -2, 2),  # Catch-all for looking away
        ]
        
        # Heatmap (10x10 grid)
        self.heatmap_rows = 10
        self.heatmap_cols = 10
        self.heatmap: Dict[Tuple[int, int], GazeHeatmapCell] = {}
        
        # Tracking state
        self.last_gaze_time = 0
        self.continuous_off_screen_time = 0
        self.distraction_count = 0
        self.rapid_movement_count = 0
        
    def add_gaze_point(self, landmarks, image_width: int, image_height: int):
        """Add a new gaze measurement"""
        gaze = self.estimator.estimate_gaze(landmarks, image_width, image_height)
        
        if gaze:
            self.history.append(gaze)
            self._update_heatmap(gaze)
            self._detect_anomalies(gaze)
            
    def add_gaze_from_data(self, gaze_data: dict):
        """Add gaze from pre-computed data"""
        gaze = GazePoint(
            timestamp=gaze_data.get('timestamp', datetime.utcnow().timestamp() * 1000),
            x=gaze_data.get('x', 0),
            y=gaze_data.get('y', 0),
            confidence=gaze_data.get('confidence', 0.8)
        )
        
        self.history.append(gaze)
        self._update_heatmap(gaze)
        self._detect_anomalies(gaze)
    
    def _update_heatmap(self, gaze: GazePoint):
        """Update attention heatmap"""
        # Convert normalized coordinates to grid cell
        col = int((gaze.x + 1) / 2 * self.heatmap_cols)
        row = int((gaze.y + 1) / 2 * self.heatmap_rows)
        
        col = max(0, min(col, self.heatmap_cols - 1))
        row = max(0, min(row, self.heatmap_rows - 1))
        
        key = (row, col)
        
        if key not in self.heatmap:
            self.heatmap[key] = GazeHeatmapCell(row=row, col=col)
            
        # Estimate duration since last point
        if len(self.history) >= 2:
            duration = gaze.timestamp - self.history[-2].timestamp
            self.heatmap[key].duration_ms += duration
            
        self.heatmap[key].visit_count += 1
    
    def _detect_anomalies(self, gaze: GazePoint):
        """Detect suspicious gaze patterns"""
        # Check if looking off screen
        if abs(gaze.x) > 0.8 or abs(gaze.y) > 0.8:
            if self.last_gaze_time > 0:
                self.continuous_off_screen_time += gaze.timestamp - self.last_gaze_time
                
                # If looking away for > 3 seconds, count as distraction
                if self.continuous_off_screen_time > 3000:
                    self.distraction_count += 1
                    self.continuous_off_screen_time = 0
        else:
            self.continuous_off_screen_time = 0
            
        # Detect rapid eye movements (saccades)
        if len(self.history) >= 2:
            prev = self.history[-2]
            dx = abs(gaze.x - prev.x)
            dy = abs(gaze.y - prev.y)
            dt = gaze.timestamp - prev.timestamp
            
            if dt > 0:
                speed = math.sqrt(dx**2 + dy**2) / dt * 1000  # per second
                
                # Very fast movement might indicate looking at another screen
                if speed > 5:  # Threshold for suspicious speed
                    self.rapid_movement_count += 1
                    
        self.last_gaze_time = gaze.timestamp
    
    def get_current_zone(self) -> str:
        """Get which zone the user is currently looking at"""
        if not self.history:
            return "unknown"
            
        gaze = self.history[-1]
        
        for zone in self.zones:
            if (zone.x_min <= gaze.x <= zone.x_max and 
                zone.y_min <= gaze.y <= zone.y_max):
                return zone.name
                
        return "off_screen"
    
    def get_zone_times(self) -> Dict[str, float]:
        """Get time spent in each zone"""
        zone_times = {zone.name: 0.0 for zone in self.zones}
        
        for i in range(1, len(self.history)):
            prev = self.history[i - 1]
            curr = self.history[i]
            
            duration = curr.timestamp - prev.timestamp
            
            for zone in self.zones:
                if (zone.x_min <= prev.x <= zone.x_max and 
                    zone.y_min <= prev.y <= zone.y_max):
                    zone_times[zone.name] += duration
                    break
                    
        return zone_times
    
    def get_attention_score(self) -> float:
        """Calculate attention score (0-100)"""
        if not self.history:
            return 100.0
            
        zone_times = self.get_zone_times()
        total_time = sum(zone_times.values()) or 1
        
        # Time in center zones is good
        center_zones = ['center', 'top_center', 'bottom_center']
        center_time = sum(zone_times.get(z, 0) for z in center_zones)
        
        # Time off screen is bad
        off_screen_time = zone_times.get('off_screen', 0)
        
        # Calculate score
        center_ratio = center_time / total_time
        off_screen_ratio = off_screen_time / total_time
        
        score = 100 * center_ratio - 50 * off_screen_ratio
        score -= self.distraction_count * 5  # Penalty for distractions
        score -= self.rapid_movement_count * 2  # Small penalty for rapid movements
        
        return max(0, min(100, score))
    
    def detect_reading_pattern(self) -> bool:
        """Detect if user is reading (horizontal scanning patterns)"""
        if len(self.history) < 20:
            return False
            
        recent = list(self.history)[-50:]
        
        # Look for horizontal sweeps
        horizontal_sweeps = 0
        
        for i in range(len(recent) - 5):
            segment = recent[i:i+5]
            
            # Check if x values increase steadily (left-to-right reading)
            x_values = [g.x for g in segment]
            if all(x_values[j] < x_values[j+1] for j in range(len(x_values)-1)):
                # Check if y values are relatively stable
                y_values = [g.y for g in segment]
                if np.std(y_values) < 0.1:
                    horizontal_sweeps += 1
                    
        return horizontal_sweeps >= 3
    
    def get_heatmap_data(self) -> List[List[float]]:
        """Get heatmap as 2D array for visualization"""
        heatmap = [[0.0] * self.heatmap_cols for _ in range(self.heatmap_rows)]
        
        max_duration = max((cell.duration_ms for cell in self.heatmap.values()), default=1)
        
        for (row, col), cell in self.heatmap.items():
            heatmap[row][col] = cell.duration_ms / max_duration
            
        return heatmap


# =============================================================================
# Gaze Analysis Service
# =============================================================================

class GazeAnalysisService:
    """
    Main service for gaze tracking and analysis.
    """
    
    def __init__(self):
        self.trackers: Dict[str, GazeTracker] = {}
        
        # Initialize MediaPipe if available
        self.face_mesh = None
        if MEDIAPIPE_AVAILABLE:
            try:
                mp_face_mesh = mp.solutions.face_mesh
                self.face_mesh = mp_face_mesh.FaceMesh(
                    max_num_faces=1,
                    refine_landmarks=True,  # Include iris landmarks
                    min_detection_confidence=0.5,
                    min_tracking_confidence=0.5
                )
            except Exception as e:
                print(f"[GazeService] Could not initialize FaceMesh: {e}")
                
    def get_tracker(self, student_id: str) -> GazeTracker:
        """Get or create tracker for student"""
        if student_id not in self.trackers:
            self.trackers[student_id] = GazeTracker()
        return self.trackers[student_id]
    
    def process_frame(self, student_id: str, frame) -> Optional[GazePoint]:
        """
        Process a webcam frame and extract gaze.
        
        Args:
            student_id: Student identifier
            frame: numpy array (RGB image)
            
        Returns:
            GazePoint if detected, None otherwise
        """
        if not self.face_mesh:
            return None
            
        try:
            results = self.face_mesh.process(frame)
            
            if results.multi_face_landmarks:
                landmarks = results.multi_face_landmarks[0].landmark
                
                tracker = self.get_tracker(student_id)
                height, width = frame.shape[:2]
                tracker.add_gaze_point(landmarks, width, height)
                
                if tracker.history:
                    return tracker.history[-1]
                    
        except Exception as e:
            print(f"[GazeService] Error processing frame: {e}")
            
        return None
    
    def process_gaze_data(self, student_id: str, gaze_data: dict):
        """Process pre-computed gaze data (from client-side detection)"""
        tracker = self.get_tracker(student_id)
        tracker.add_gaze_from_data(gaze_data)
    
    def get_analysis(self, student_id: str) -> GazeAnalysis:
        """Get complete gaze analysis for a student"""
        tracker = self.get_tracker(student_id)
        
        # Get current gaze
        current_gaze = tracker.history[-1] if tracker.history else None
        
        analysis = GazeAnalysis(
            student_id=student_id,
            timestamp=datetime.utcnow().isoformat(),
            current_gaze_x=current_gaze.x if current_gaze else 0,
            current_gaze_y=current_gaze.y if current_gaze else 0,
            looking_at_screen=abs(current_gaze.x) < 0.8 and abs(current_gaze.y) < 0.8 if current_gaze else True,
            attention_score=tracker.get_attention_score(),
            distraction_count=tracker.distraction_count,
            looking_away_duration_ms=tracker.continuous_off_screen_time,
            rapid_eye_movement_count=tracker.rapid_movement_count,
            reading_pattern_detected=tracker.detect_reading_pattern(),
            time_in_zones=tracker.get_zone_times(),
            current_zone=tracker.get_current_zone(),
        )
        
        # Detect anomalies
        anomalies = []
        
        if tracker.distraction_count > 5:
            anomalies.append("excessive_distractions")
            analysis.anomaly_score += 20
            
        if tracker.rapid_movement_count > 20:
            anomalies.append("suspicious_eye_movements")
            analysis.anomaly_score += 15
            
        if not analysis.looking_at_screen:
            anomalies.append("looking_away")
            analysis.anomaly_score += 10
            
        if tracker.continuous_off_screen_time > 5000:
            anomalies.append("prolonged_off_screen")
            analysis.anomaly_score += 25
            
        analysis.anomalies = anomalies
        analysis.anomaly_score = min(100, analysis.anomaly_score)
        
        return analysis
    
    def get_heatmap(self, student_id: str) -> Dict:
        """Get attention heatmap for visualization"""
        tracker = self.get_tracker(student_id)
        
        return {
            'student_id': student_id,
            'heatmap': tracker.get_heatmap_data(),
            'rows': tracker.heatmap_rows,
            'cols': tracker.heatmap_cols,
        }
    
    def reset_tracker(self, student_id: str):
        """Reset tracker for new session"""
        if student_id in self.trackers:
            del self.trackers[student_id]


# =============================================================================
# Singleton Instance
# =============================================================================

_gaze_service: Optional[GazeAnalysisService] = None

def get_gaze_service() -> GazeAnalysisService:
    """Get singleton gaze analysis service"""
    global _gaze_service
    if _gaze_service is None:
        _gaze_service = GazeAnalysisService()
    return _gaze_service
