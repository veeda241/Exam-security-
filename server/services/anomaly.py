"""
ExamGuard Pro - Anomaly Detection Module
Rule-based and pattern-based anomaly detection
"""

from typing import Dict, Any, List
from datetime import datetime, timedelta
from config import RISK_WEIGHTS


class AnomalyDetector:
    """Behavior anomaly detection using rules and patterns"""
    
    def __init__(self):
        # Thresholds for anomaly detection
        self.thresholds = {
            "tab_switches_per_minute": 3,
            "copy_events_per_minute": 2,
            "face_absence_percentage": 20,  # % of time
            "rapid_event_interval_ms": 500,  # Events too close together
        }
    
    def analyze_session_behavior(
        self,
        events: List[Dict],
        session_duration_seconds: float
    ) -> Dict[str, Any]:
        """
        Analyze session behavior for anomalies
        
        Args:
            events: List of event dictionaries
            session_duration_seconds: Total session duration
        """
        
        if not events or session_duration_seconds <= 0:
            return {
                "anomalies": [],
                "anomaly_count": 0,
                "risk_score": 0,
            }
        
        anomalies = []
        duration_minutes = session_duration_seconds / 60
        
        # Count event types
        event_counts = {}
        timestamps = []
        
        for event in events:
            event_type = event.get("event_type", event.get("type", "UNKNOWN"))
            event_counts[event_type] = event_counts.get(event_type, 0) + 1
            
            ts = event.get("timestamp") or event.get("client_timestamp")
            if ts:
                timestamps.append(ts)
        
        # Check 1: Tab switch frequency
        tab_switches = event_counts.get("TAB_SWITCH", 0)
        tab_switch_rate = tab_switches / max(duration_minutes, 1)
        
        if tab_switch_rate > self.thresholds["tab_switches_per_minute"]:
            anomalies.append({
                "type": "HIGH_TAB_SWITCH_RATE",
                "description": f"Tab switch rate ({tab_switch_rate:.1f}/min) exceeds threshold",
                "value": tab_switch_rate,
                "threshold": self.thresholds["tab_switches_per_minute"],
                "severity": "high",
            })
        
        # Check 2: Copy event frequency
        copy_events = event_counts.get("COPY", 0) + event_counts.get("PASTE", 0)
        copy_rate = copy_events / max(duration_minutes, 1)
        
        if copy_rate > self.thresholds["copy_events_per_minute"]:
            anomalies.append({
                "type": "HIGH_COPY_RATE",
                "description": f"Copy/paste rate ({copy_rate:.1f}/min) exceeds threshold",
                "value": copy_rate,
                "threshold": self.thresholds["copy_events_per_minute"],
                "severity": "medium",
            })
        
        # Check 3: Face absence frequency
        face_absences = event_counts.get("FACE_ABSENT", 0)
        total_checks = face_absences + event_counts.get("FACE_PRESENT", 0)
        
        if total_checks > 0:
            absence_percentage = (face_absences / total_checks) * 100
            if absence_percentage > self.thresholds["face_absence_percentage"]:
                anomalies.append({
                    "type": "HIGH_FACE_ABSENCE",
                    "description": f"Face absence ({absence_percentage:.1f}%) exceeds threshold",
                    "value": absence_percentage,
                    "threshold": self.thresholds["face_absence_percentage"],
                    "severity": "high",
                })
        
        # Check 4: Rapid event bursts
        if len(timestamps) > 1:
            sorted_ts = sorted(timestamps)
            rapid_intervals = 0
            
            for i in range(1, len(sorted_ts)):
                interval = sorted_ts[i] - sorted_ts[i-1]
                if isinstance(interval, timedelta):
                    interval = interval.total_seconds() * 1000
                
                if interval < self.thresholds["rapid_event_interval_ms"]:
                    rapid_intervals += 1
            
            if rapid_intervals > 5:
                anomalies.append({
                    "type": "RAPID_EVENT_BURST",
                    "description": f"Detected {rapid_intervals} rapid event sequences",
                    "value": rapid_intervals,
                    "threshold": 5,
                    "severity": "low",
                })
        
        # Check 5: Forbidden site access
        forbidden_count = event_counts.get("FORBIDDEN_SITE", 0) + event_counts.get("FORBIDDEN_CONTENT", 0)
        if forbidden_count > 0:
            anomalies.append({
                "type": "FORBIDDEN_ACCESS",
                "description": f"Accessed {forbidden_count} forbidden sites/content",
                "value": forbidden_count,
                "threshold": 0,
                "severity": "critical",
            })
        
        # Check 6: Screen share stopped
        if event_counts.get("SCREEN_SHARE_STOPPED", 0) > 0:
            anomalies.append({
                "type": "SCREEN_SHARE_STOPPED",
                "description": "User stopped screen sharing during exam",
                "value": event_counts["SCREEN_SHARE_STOPPED"],
                "threshold": 0,
                "severity": "critical",
            })
        
        # Calculate risk score from anomalies
        risk_score = 0
        for anomaly in anomalies:
            if anomaly["severity"] == "critical":
                risk_score += 30
            elif anomaly["severity"] == "high":
                risk_score += 20
            elif anomaly["severity"] == "medium":
                risk_score += 10
            else:
                risk_score += 5
        
        return {
            "anomalies": anomalies,
            "anomaly_count": len(anomalies),
            "risk_score": min(risk_score, 100),
            "event_summary": event_counts,
        }
    
    def check_single_event(self, event: Dict, previous_events: List[Dict] = None) -> Dict[str, Any]:
        """Quick check for single event anomalies"""
        
        event_type = event.get("event_type", event.get("type", "UNKNOWN"))
        
        # Immediate red flags
        critical_events = ["FORBIDDEN_SITE", "FORBIDDEN_CONTENT", "SCREEN_SHARE_STOPPED"]
        
        if event_type in critical_events:
            return {
                "is_anomaly": True,
                "severity": "critical",
                "description": f"Critical event detected: {event_type}",
                "immediate_flag": True,
            }
        
        return {
            "is_anomaly": False,
            "severity": "none",
            "immediate_flag": False,
        }


# Global detector instance
_detector = None


def get_detector() -> AnomalyDetector:
    """Get or create anomaly detector"""
    global _detector
    if _detector is None:
        _detector = AnomalyDetector()
    return _detector


async def detect_anomalies(
    events: List[Dict],
    session_duration_seconds: float
) -> Dict[str, Any]:
    """
    Detect behavioral anomalies in session events
    
    Args:
        events: List of event dictionaries
        session_duration_seconds: Total session duration
        
    Returns:
        Dictionary with anomaly detection results:
        - anomalies: List of detected anomalies
        - anomaly_count: int
        - risk_score: float
    """
    detector = get_detector()
    return detector.analyze_session_behavior(events, session_duration_seconds)
