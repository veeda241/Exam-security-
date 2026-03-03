"""
ExamGuard Pro - Behavioral Biometrics Engine
Analyzes keystroke dynamics, mouse patterns, and interaction behavior
to create unique behavioral fingerprints for identity verification.

100% LOCAL - No external APIs required
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from collections import deque
import json
import hashlib


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class KeystrokeEvent:
    """Single keystroke event"""
    key: str
    event_type: str  # 'keydown' or 'keyup'
    timestamp: float  # milliseconds
    
@dataclass
class MouseEvent:
    """Single mouse event"""
    x: int
    y: int
    event_type: str  # 'move', 'click', 'scroll'
    timestamp: float
    button: Optional[int] = None
    scroll_delta: Optional[int] = None


@dataclass
class BiometricProfile:
    """Behavioral biometric profile for a student"""
    student_id: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    # Keystroke features
    avg_dwell_time: float = 0.0  # Time key is held down
    avg_flight_time: float = 0.0  # Time between key releases and next key press
    typing_speed_wpm: float = 0.0
    key_hold_variance: float = 0.0
    digraph_timings: Dict[str, float] = field(default_factory=dict)  # Two-key combinations
    
    # Mouse features
    avg_mouse_speed: float = 0.0
    avg_mouse_acceleration: float = 0.0
    click_frequency: float = 0.0
    movement_smoothness: float = 0.0  # Curvature analysis
    preferred_click_zones: List[Tuple[int, int]] = field(default_factory=list)
    
    # Scroll features
    avg_scroll_speed: float = 0.0
    scroll_direction_ratio: float = 0.5  # Up vs down ratio
    
    # Combined signature
    signature_hash: str = ""
    confidence_score: float = 0.0
    sample_count: int = 0


# =============================================================================
# Keystroke Dynamics Analyzer
# =============================================================================

class KeystrokeDynamicsAnalyzer:
    """
    Analyzes typing patterns to create unique behavioral fingerprints.
    
    Features extracted:
    - Dwell time: How long each key is pressed
    - Flight time: Time between releasing one key and pressing next
    - Digraph latency: Time for specific two-key combinations
    - Typing rhythm: Variance in timing patterns
    - Error patterns: Backspace usage patterns
    """
    
    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self.key_events: deque = deque(maxlen=window_size * 2)
        self.key_down_times: Dict[str, float] = {}
        
    def add_event(self, event: KeystrokeEvent):
        """Add a keystroke event for analysis"""
        self.key_events.append(event)
        
        if event.event_type == 'keydown':
            self.key_down_times[event.key] = event.timestamp
            
    def calculate_dwell_times(self) -> List[float]:
        """Calculate how long keys are held down"""
        dwell_times = []
        key_downs = {}
        
        for event in self.key_events:
            if event.event_type == 'keydown':
                key_downs[event.key] = event.timestamp
            elif event.event_type == 'keyup' and event.key in key_downs:
                dwell = event.timestamp - key_downs[event.key]
                if 0 < dwell < 1000:  # Reasonable range (0-1 second)
                    dwell_times.append(dwell)
                del key_downs[event.key]
                
        return dwell_times
    
    def calculate_flight_times(self) -> List[float]:
        """Calculate time between key release and next key press"""
        flight_times = []
        last_keyup_time = None
        
        for event in self.key_events:
            if event.event_type == 'keyup':
                last_keyup_time = event.timestamp
            elif event.event_type == 'keydown' and last_keyup_time is not None:
                flight = event.timestamp - last_keyup_time
                if 0 < flight < 2000:  # Reasonable range
                    flight_times.append(flight)
                    
        return flight_times
    
    def calculate_digraph_timings(self) -> Dict[str, List[float]]:
        """Calculate timing for two-key combinations (digraphs)"""
        digraphs: Dict[str, List[float]] = {}
        keydowns = list(filter(lambda e: e.event_type == 'keydown', self.key_events))
        
        for i in range(len(keydowns) - 1):
            key1 = keydowns[i]
            key2 = keydowns[i + 1]
            
            # Only consider letter keys
            if key1.key.isalpha() and key2.key.isalpha():
                digraph = f"{key1.key.lower()}{key2.key.lower()}"
                timing = key2.timestamp - key1.timestamp
                
                if 0 < timing < 1000:
                    if digraph not in digraphs:
                        digraphs[digraph] = []
                    digraphs[digraph].append(timing)
                    
        return digraphs
    
    def calculate_typing_speed(self) -> float:
        """Calculate typing speed in WPM"""
        keydowns = list(filter(lambda e: e.event_type == 'keydown', self.key_events))
        
        if len(keydowns) < 2:
            return 0.0
            
        # Count character keys (excluding modifiers)
        char_keys = [k for k in keydowns if len(k.key) == 1]
        
        if len(char_keys) < 2:
            return 0.0
            
        time_span = (char_keys[-1].timestamp - char_keys[0].timestamp) / 1000 / 60  # minutes
        
        if time_span <= 0:
            return 0.0
            
        # Approximate words (5 characters per word)
        words = len(char_keys) / 5
        
        return words / time_span
    
    def extract_features(self) -> Dict[str, float]:
        """Extract all keystroke features"""
        dwell_times = self.calculate_dwell_times()
        flight_times = self.calculate_flight_times()
        digraphs = self.calculate_digraph_timings()
        
        features = {
            'avg_dwell_time': np.mean(dwell_times) if dwell_times else 0,
            'std_dwell_time': np.std(dwell_times) if dwell_times else 0,
            'avg_flight_time': np.mean(flight_times) if flight_times else 0,
            'std_flight_time': np.std(flight_times) if flight_times else 0,
            'typing_speed_wpm': self.calculate_typing_speed(),
            'dwell_variance': np.var(dwell_times) if dwell_times else 0,
            'flight_variance': np.var(flight_times) if flight_times else 0,
            'total_keystrokes': len(list(filter(lambda e: e.event_type == 'keydown', self.key_events))),
        }
        
        # Add common digraph timings
        common_digraphs = ['th', 'he', 'in', 'er', 'an', 'on', 'en', 'at', 'es', 'ed']
        for dg in common_digraphs:
            if dg in digraphs and digraphs[dg]:
                features[f'digraph_{dg}'] = np.mean(digraphs[dg])
            else:
                features[f'digraph_{dg}'] = 0
                
        return features
    
    def reset(self):
        """Clear all stored events"""
        self.key_events.clear()
        self.key_down_times.clear()


# =============================================================================
# Mouse Dynamics Analyzer
# =============================================================================

class MouseDynamicsAnalyzer:
    """
    Analyzes mouse movement patterns for behavioral fingerprinting.
    
    Features extracted:
    - Movement speed and acceleration
    - Path curvature and smoothness
    - Click patterns and frequencies
    - Movement direction preferences
    - Pause patterns
    """
    
    def __init__(self, window_size: int = 500):
        self.window_size = window_size
        self.mouse_events: deque = deque(maxlen=window_size)
        
    def add_event(self, event: MouseEvent):
        """Add a mouse event for analysis"""
        self.mouse_events.append(event)
        
    def calculate_speeds(self) -> List[float]:
        """Calculate mouse movement speeds"""
        speeds = []
        moves = [e for e in self.mouse_events if e.event_type == 'move']
        
        for i in range(1, len(moves)):
            prev = moves[i - 1]
            curr = moves[i]
            
            dx = curr.x - prev.x
            dy = curr.y - prev.y
            dt = (curr.timestamp - prev.timestamp) / 1000  # seconds
            
            if dt > 0:
                distance = np.sqrt(dx**2 + dy**2)
                speed = distance / dt
                if speed < 10000:  # Filter unrealistic speeds
                    speeds.append(speed)
                    
        return speeds
    
    def calculate_accelerations(self) -> List[float]:
        """Calculate mouse acceleration"""
        speeds = self.calculate_speeds()
        accelerations = []
        
        moves = [e for e in self.mouse_events if e.event_type == 'move']
        
        for i in range(1, len(speeds)):
            if i < len(moves) - 1:
                dt = (moves[i + 1].timestamp - moves[i].timestamp) / 1000
                if dt > 0:
                    acc = (speeds[i] - speeds[i - 1]) / dt
                    if abs(acc) < 100000:  # Filter outliers
                        accelerations.append(acc)
                        
        return accelerations
    
    def calculate_curvature(self) -> List[float]:
        """Calculate path curvature (smoothness indicator)"""
        curvatures = []
        moves = [e for e in self.mouse_events if e.event_type == 'move']
        
        for i in range(2, len(moves)):
            p1 = (moves[i - 2].x, moves[i - 2].y)
            p2 = (moves[i - 1].x, moves[i - 1].y)
            p3 = (moves[i].x, moves[i].y)
            
            # Calculate angle change
            v1 = (p2[0] - p1[0], p2[1] - p1[1])
            v2 = (p3[0] - p2[0], p3[1] - p2[1])
            
            mag1 = np.sqrt(v1[0]**2 + v1[1]**2)
            mag2 = np.sqrt(v2[0]**2 + v2[1]**2)
            
            if mag1 > 0 and mag2 > 0:
                dot = v1[0] * v2[0] + v1[1] * v2[1]
                cos_angle = np.clip(dot / (mag1 * mag2), -1, 1)
                angle = np.arccos(cos_angle)
                curvatures.append(angle)
                
        return curvatures
    
    def calculate_click_frequency(self) -> float:
        """Calculate clicks per minute"""
        clicks = [e for e in self.mouse_events if e.event_type == 'click']
        
        if len(clicks) < 2:
            return 0.0
            
        time_span = (clicks[-1].timestamp - clicks[0].timestamp) / 1000 / 60  # minutes
        
        if time_span <= 0:
            return 0.0
            
        return len(clicks) / time_span
    
    def calculate_movement_direction_histogram(self) -> Dict[str, float]:
        """Analyze preferred movement directions"""
        directions = {'up': 0, 'down': 0, 'left': 0, 'right': 0}
        moves = [e for e in self.mouse_events if e.event_type == 'move']
        
        for i in range(1, len(moves)):
            dx = moves[i].x - moves[i - 1].x
            dy = moves[i].y - moves[i - 1].y
            
            if abs(dx) > abs(dy):
                if dx > 0:
                    directions['right'] += 1
                else:
                    directions['left'] += 1
            else:
                if dy > 0:
                    directions['down'] += 1
                else:
                    directions['up'] += 1
                    
        total = sum(directions.values()) or 1
        return {k: v / total for k, v in directions.items()}
    
    def extract_features(self) -> Dict[str, float]:
        """Extract all mouse features"""
        speeds = self.calculate_speeds()
        accelerations = self.calculate_accelerations()
        curvatures = self.calculate_curvature()
        directions = self.calculate_movement_direction_histogram()
        
        features = {
            'avg_speed': np.mean(speeds) if speeds else 0,
            'std_speed': np.std(speeds) if speeds else 0,
            'max_speed': np.max(speeds) if speeds else 0,
            'avg_acceleration': np.mean(accelerations) if accelerations else 0,
            'std_acceleration': np.std(accelerations) if accelerations else 0,
            'avg_curvature': np.mean(curvatures) if curvatures else 0,
            'std_curvature': np.std(curvatures) if curvatures else 0,
            'smoothness': 1 / (1 + np.std(curvatures)) if curvatures else 0,
            'click_frequency': self.calculate_click_frequency(),
            'direction_up': directions.get('up', 0.25),
            'direction_down': directions.get('down', 0.25),
            'direction_left': directions.get('left', 0.25),
            'direction_right': directions.get('right', 0.25),
            'total_movements': len([e for e in self.mouse_events if e.event_type == 'move']),
        }
        
        return features
    
    def reset(self):
        """Clear all stored events"""
        self.mouse_events.clear()


# =============================================================================
# Biometric Identity Verifier
# =============================================================================

class BiometricVerifier:
    """
    Verifies student identity by comparing current behavior to stored profile.
    Uses local ML techniques - no external APIs.
    """
    
    def __init__(self, similarity_threshold: float = 0.7):
        self.similarity_threshold = similarity_threshold
        self.keystroke_analyzer = KeystrokeDynamicsAnalyzer()
        self.mouse_analyzer = MouseDynamicsAnalyzer()
        self.profiles: Dict[str, BiometricProfile] = {}
        
    def process_keystroke(self, student_id: str, event_data: dict):
        """Process a keystroke event"""
        event = KeystrokeEvent(
            key=event_data.get('key', ''),
            event_type=event_data.get('type', 'keydown'),
            timestamp=event_data.get('timestamp', 0)
        )
        self.keystroke_analyzer.add_event(event)
        
    def process_mouse(self, student_id: str, event_data: dict):
        """Process a mouse event"""
        event = MouseEvent(
            x=event_data.get('x', 0),
            y=event_data.get('y', 0),
            event_type=event_data.get('type', 'move'),
            timestamp=event_data.get('timestamp', 0),
            button=event_data.get('button'),
            scroll_delta=event_data.get('scrollDelta')
        )
        self.mouse_analyzer.add_event(event)
        
    def extract_current_features(self) -> Dict[str, float]:
        """Extract features from current session"""
        keystroke_features = self.keystroke_analyzer.extract_features()
        mouse_features = self.mouse_analyzer.extract_features()
        
        return {**keystroke_features, **mouse_features}
    
    def create_profile(self, student_id: str) -> BiometricProfile:
        """Create a biometric profile from current session data"""
        features = self.extract_current_features()
        
        profile = BiometricProfile(
            student_id=student_id,
            avg_dwell_time=features.get('avg_dwell_time', 0),
            avg_flight_time=features.get('avg_flight_time', 0),
            typing_speed_wpm=features.get('typing_speed_wpm', 0),
            key_hold_variance=features.get('dwell_variance', 0),
            avg_mouse_speed=features.get('avg_speed', 0),
            avg_mouse_acceleration=features.get('avg_acceleration', 0),
            click_frequency=features.get('click_frequency', 0),
            movement_smoothness=features.get('smoothness', 0),
        )
        
        # Create signature hash
        feature_str = json.dumps(features, sort_keys=True)
        profile.signature_hash = hashlib.sha256(feature_str.encode()).hexdigest()[:16]
        
        self.profiles[student_id] = profile
        return profile
    
    def verify_identity(self, student_id: str) -> Tuple[bool, float, Dict]:
        """
        Verify if current behavior matches stored profile.
        
        Returns:
            (is_verified, confidence_score, details)
        """
        if student_id not in self.profiles:
            return False, 0.0, {'error': 'No profile found for student'}
            
        stored_profile = self.profiles[student_id]
        current_features = self.extract_current_features()
        
        # Calculate similarity for each feature group
        keystroke_sim = self._calculate_keystroke_similarity(stored_profile, current_features)
        mouse_sim = self._calculate_mouse_similarity(stored_profile, current_features)
        
        # Weighted combination
        overall_sim = 0.6 * keystroke_sim + 0.4 * mouse_sim
        
        is_verified = overall_sim >= self.similarity_threshold
        
        details = {
            'keystroke_similarity': keystroke_sim,
            'mouse_similarity': mouse_sim,
            'overall_similarity': overall_sim,
            'threshold': self.similarity_threshold,
            'features_compared': len(current_features),
        }
        
        return is_verified, overall_sim, details
    
    def _calculate_keystroke_similarity(self, profile: BiometricProfile, features: Dict) -> float:
        """Calculate keystroke pattern similarity"""
        comparisons = [
            self._feature_similarity(profile.avg_dwell_time, features.get('avg_dwell_time', 0), 50),
            self._feature_similarity(profile.avg_flight_time, features.get('avg_flight_time', 0), 100),
            self._feature_similarity(profile.typing_speed_wpm, features.get('typing_speed_wpm', 0), 20),
        ]
        
        valid = [c for c in comparisons if c is not None]
        return np.mean(valid) if valid else 0.5
    
    def _calculate_mouse_similarity(self, profile: BiometricProfile, features: Dict) -> float:
        """Calculate mouse pattern similarity"""
        comparisons = [
            self._feature_similarity(profile.avg_mouse_speed, features.get('avg_speed', 0), 500),
            self._feature_similarity(profile.movement_smoothness, features.get('smoothness', 0), 0.5),
            self._feature_similarity(profile.click_frequency, features.get('click_frequency', 0), 30),
        ]
        
        valid = [c for c in comparisons if c is not None]
        return np.mean(valid) if valid else 0.5
    
    def _feature_similarity(self, stored: float, current: float, tolerance: float) -> float:
        """Calculate similarity between two feature values"""
        if stored == 0 and current == 0:
            return 1.0
        if stored == 0 or tolerance == 0:
            return 0.5
            
        diff = abs(stored - current)
        similarity = max(0, 1 - (diff / tolerance))
        return similarity
    
    def get_anomaly_score(self, student_id: str) -> float:
        """
        Calculate anomaly score (0-100) for current behavior.
        Higher = more anomalous/suspicious.
        """
        is_verified, similarity, _ = self.verify_identity(student_id)
        
        # Convert similarity to anomaly score
        anomaly_score = (1 - similarity) * 100
        
        return min(100, max(0, anomaly_score))
    
    def reset_session(self):
        """Reset analyzers for new session"""
        self.keystroke_analyzer.reset()
        self.mouse_analyzer.reset()


# =============================================================================
# Scroll Behavior Analyzer
# =============================================================================

class ScrollBehaviorAnalyzer:
    """Analyzes scroll patterns for additional behavioral signals"""
    
    def __init__(self):
        self.scroll_events: List[MouseEvent] = []
        
    def add_scroll(self, event: MouseEvent):
        """Add a scroll event"""
        if event.event_type == 'scroll':
            self.scroll_events.append(event)
            
    def extract_features(self) -> Dict[str, float]:
        """Extract scroll behavior features"""
        if not self.scroll_events:
            return {
                'avg_scroll_speed': 0,
                'scroll_direction_ratio': 0.5,
                'scroll_frequency': 0,
            }
            
        # Calculate scroll speeds
        speeds = []
        up_count = 0
        down_count = 0
        
        for i in range(1, len(self.scroll_events)):
            prev = self.scroll_events[i - 1]
            curr = self.scroll_events[i]
            
            dt = (curr.timestamp - prev.timestamp) / 1000
            if dt > 0 and curr.scroll_delta:
                speed = abs(curr.scroll_delta) / dt
                speeds.append(speed)
                
                if curr.scroll_delta > 0:
                    down_count += 1
                else:
                    up_count += 1
                    
        total = up_count + down_count or 1
        
        # Scroll frequency
        if len(self.scroll_events) >= 2:
            time_span = (self.scroll_events[-1].timestamp - self.scroll_events[0].timestamp) / 1000 / 60
            frequency = len(self.scroll_events) / time_span if time_span > 0 else 0
        else:
            frequency = 0
            
        return {
            'avg_scroll_speed': np.mean(speeds) if speeds else 0,
            'scroll_direction_ratio': up_count / total,
            'scroll_frequency': frequency,
        }


# =============================================================================
# Main Biometrics Service
# =============================================================================

class BiometricsService:
    """
    Main service for behavioral biometrics analysis.
    Orchestrates all analyzers and provides unified API.
    """
    
    def __init__(self):
        self.verifiers: Dict[str, BiometricVerifier] = {}
        self.scroll_analyzers: Dict[str, ScrollBehaviorAnalyzer] = {}
        
    def get_verifier(self, student_id: str) -> BiometricVerifier:
        """Get or create verifier for student"""
        if student_id not in self.verifiers:
            self.verifiers[student_id] = BiometricVerifier()
        return self.verifiers[student_id]
    
    def get_scroll_analyzer(self, student_id: str) -> ScrollBehaviorAnalyzer:
        """Get or create scroll analyzer for student"""
        if student_id not in self.scroll_analyzers:
            self.scroll_analyzers[student_id] = ScrollBehaviorAnalyzer()
        return self.scroll_analyzers[student_id]
    
    def process_event(self, student_id: str, event_type: str, event_data: dict):
        """Process any biometric event"""
        verifier = self.get_verifier(student_id)
        
        if event_type == 'keystroke':
            verifier.process_keystroke(student_id, event_data)
        elif event_type == 'mouse':
            verifier.process_mouse(student_id, event_data)
            if event_data.get('type') == 'scroll':
                scroll_analyzer = self.get_scroll_analyzer(student_id)
                scroll_analyzer.add_scroll(MouseEvent(
                    x=event_data.get('x', 0),
                    y=event_data.get('y', 0),
                    event_type='scroll',
                    timestamp=event_data.get('timestamp', 0),
                    scroll_delta=event_data.get('scrollDelta', 0)
                ))
                
    def get_full_analysis(self, student_id: str) -> Dict:
        """Get complete biometric analysis for a student"""
        verifier = self.get_verifier(student_id)
        scroll_analyzer = self.get_scroll_analyzer(student_id)
        
        keystroke_features = verifier.keystroke_analyzer.extract_features()
        mouse_features = verifier.mouse_analyzer.extract_features()
        scroll_features = scroll_analyzer.extract_features()
        
        # Get verification if profile exists
        is_verified, similarity, details = verifier.verify_identity(student_id)
        
        return {
            'student_id': student_id,
            'timestamp': datetime.utcnow().isoformat(),
            'keystroke': keystroke_features,
            'mouse': mouse_features,
            'scroll': scroll_features,
            'identity_verification': {
                'verified': is_verified,
                'similarity': similarity,
                'details': details,
            },
            'anomaly_score': verifier.get_anomaly_score(student_id),
        }
    
    def create_baseline_profile(self, student_id: str) -> Dict:
        """Create baseline profile from current session"""
        verifier = self.get_verifier(student_id)
        profile = verifier.create_profile(student_id)
        
        return {
            'student_id': student_id,
            'profile_created': True,
            'signature_hash': profile.signature_hash,
            'typing_speed_wpm': profile.typing_speed_wpm,
            'avg_dwell_time': profile.avg_dwell_time,
            'avg_mouse_speed': profile.avg_mouse_speed,
        }


# =============================================================================
# Singleton Instance
# =============================================================================

_biometrics_service: Optional[BiometricsService] = None

def get_biometrics_service() -> BiometricsService:
    """Get singleton biometrics service instance"""
    global _biometrics_service
    if _biometrics_service is None:
        _biometrics_service = BiometricsService()
    return _biometrics_service
