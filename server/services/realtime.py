"""
ExamGuard Pro - Real-Time Monitoring Service
WebSocket-based real-time event broadcasting and monitoring
"""

import json
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, asdict
from enum import Enum
import numpy as np
from fastapi import WebSocket, WebSocketDisconnect


class AlertLevel(str, Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class EventType(str, Enum):
    """Types of real-time events"""
    # Session events
    SESSION_STARTED = "session_started"
    SESSION_ENDED = "session_ended"
    STUDENT_JOINED = "student_joined"
    STUDENT_LEFT = "student_left"
    
    # Monitoring events
    FACE_DETECTED = "face_detected"
    FACE_MISSING = "face_missing"
    MULTIPLE_FACES = "multiple_faces"
    
    # Suspicious activity
    TAB_SWITCH = "tab_switch"
    COPY_PASTE = "copy_paste"
    SCREENSHOT_ATTEMPT = "screenshot_attempt"
    WINDOW_BLUR = "window_blur"
    
    # Advanced detection (Layer 1-4)
    GAZE_AVERSION = "gaze_aversion"
    MOUTH_MOVEMENT = "mouth_movement"
    BEHAVIOR_VIOLATION = "behavior_violation" # Keystroke/Velocity
    QUESTION_LEAK = "question_leak"
    NETWORK_CHANGE = "network_change"
    DEVICE_MISMATCH = "device_mismatch"
    
    # Analysis events
    PLAGIARISM_DETECTED = "plagiarism_detected"
    ANOMALY_DETECTED = "anomaly_detected"
    LOW_ENGAGEMENT = "low_engagement"
    UNUSUAL_BEHAVIOR = "unusual_behavior"
    OBJECT_DETECTED = "object_detected" # Generic for AI results
    
    # System events
    RISK_SCORE_UPDATE = "risk_score_update"
    ALERT_TRIGGERED = "alert_triggered"
    REPORT_GENERATED = "report_generated"
    
    # Heartbeat
    HEARTBEAT = "heartbeat"


@dataclass
class RealtimeEvent:
    """Structure for real-time events"""
    event_type: str
    student_id: Optional[str]
    session_id: Optional[str]
    data: Dict[str, Any]
    alert_level: str
    timestamp: str
    
    def to_json(self) -> str:
        return json.dumps(asdict(self))


class RoomManager:
    """Manages WebSocket rooms for session-based broadcasting"""
    
    def __init__(self):
        self.rooms: Dict[str, Set[WebSocket]] = {}  # session_id -> connections
    
    def join_room(self, session_id: str, websocket: WebSocket):
        if session_id not in self.rooms:
            self.rooms[session_id] = set()
        self.rooms[session_id].add(websocket)
    
    def leave_room(self, session_id: str, websocket: WebSocket):
        if session_id in self.rooms:
            self.rooms[session_id].discard(websocket)
            if not self.rooms[session_id]:
                del self.rooms[session_id]
    
    def get_room_members(self, session_id: str) -> Set[WebSocket]:
        return self.rooms.get(session_id, set()).copy()


class RealtimeMonitoringManager:
    """
    Advanced WebSocket connection manager for real-time monitoring.
    
    Features:
    - Multi-room support (per session)
    - Alert broadcasting by severity
    - Student-specific notifications
    - Dashboard subscriptions
    - Heartbeat monitoring
    - Event history
    """
    
    def __init__(self, max_history: int = 100):
        # Connection pools
        self.dashboard_connections: Set[WebSocket] = set()
        self.proctor_connections: Set[WebSocket] = set()
        self.student_connections: Dict[str, WebSocket] = {}  # student_id -> ws
        
        # Room management
        self.room_manager = RoomManager()
        
        # Frame extraction for AI analysis on live streams
        from services.frame_extractor import get_frame_extractor
        self.extractor = get_frame_extractor()
        
        # Event history (for late-joiners)
        self.event_history: List[RealtimeEvent] = []
        self.max_history = max_history
        
        # Stats
        self.stats = {
            "events_sent": 0,
            "connections_total": 0,
            "alerts_sent": 0,
        }
    
    # AI Analysis Callback for live streams
    def _ai_stream_callback(self, session_id: str, frame: np.ndarray):
        """Processes an extracted frame with the AI engines (background thread)"""
        try:
            # We need the engines from the app state (circular import check)
            from main import app
            vision_engine = getattr(app.state, "vision_engine", None)
            from services.object_detection import get_object_detector
            object_detector = get_object_detector()
            
            if vision_engine:
                 # Standard face/gaze metrics
                 results = vision_engine.analyze_frame(frame, student_id=session_id)
                 if results['violations']:
                      # Broadcast alerts to session proctors
                      asyncio.run_coroutine_threadsafe(
                          self.broadcast_to_session(session_id, {
                              "type": "vision_alert",
                              "violations": results['violations'],
                              "engagement": results['engagement_score']
                          }),
                          asyncio.get_event_loop()
                      )
                      # Also broadcast for the extension to update its counters
                      for v in results['violations']:
                           asyncio.run_coroutine_threadsafe(
                               self.broadcast_to_session(session_id, {
                                   "type": "anomaly_alert",
                                   "alert_type": v,
                                   "message": f"Violation: {v}",
                                   "data": {"type": v.lower()}
                               }),
                               asyncio.get_event_loop()
                           )
            
            if object_detector:
                 # YOLO object detection
                 obj_results = object_detector.detect(frame)
                 if obj_results['phone_detected']:
                      # Send critical dashboard alert
                      asyncio.run_coroutine_threadsafe(
                          self.send_alert(
                              "phone_detected",
                              "Mobile phone detected in live stream!",
                              session_id=session_id,
                              severity=AlertLevel.CRITICAL
                          ),
                          asyncio.get_event_loop()
                      )
                      # Send immediate extension anomaly alert
                      asyncio.run_coroutine_threadsafe(
                           self.broadcast_to_session(session_id, {
                               "type": "anomaly_alert",
                               "alert_type": "PHONE_DETECTED",
                               "message": "Mobile phone detected in your webcam feed!",
                               "data": {"type": "phone_detected"}
                           }),
                           asyncio.get_event_loop()
                      )
        except Exception as e:
            print(f"[AI-Stream] Analysis error: {e}")

    @property
    def total_connections(self) -> int:
        return (
            len(self.dashboard_connections) +
            len(self.proctor_connections) +
            len(self.student_connections)
        )
    
    # =========================================================================
    # Connection Management
    # =========================================================================
    
    async def connect_dashboard(self, websocket: WebSocket):
        """Connect a dashboard client"""
        await websocket.accept()
        self.dashboard_connections.add(websocket)
        self.stats["connections_total"] += 1
        
        # Send connection confirmation
        await self._send_to_socket(websocket, {
            "type": "connection",
            "status": "connected",
            "role": "dashboard",
            "timestamp": datetime.utcnow().isoformat(),
        })
        
        # Send recent history
        await self._send_history(websocket, limit=20)
        
        print(f"[WS] Dashboard connected. Total dashboards: {len(self.dashboard_connections)}")
    
    async def connect_proctor(self, websocket: WebSocket, session_id: str):
        """Connect a proctor to monitor a specific session"""
        await websocket.accept()
        self.proctor_connections.add(websocket)
        self.room_manager.join_room(session_id, websocket)
        self.stats["connections_total"] += 1
        
        await self._send_to_socket(websocket, {
            "type": "connection",
            "status": "connected",
            "role": "proctor",
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat(),
        })
        
        print(f"[WS] Proctor connected to session {session_id}")
    
    async def connect_student(self, websocket: WebSocket, student_id: str, session_id: str):
        """Connect a student (for receiving alerts/instructions)"""
        await websocket.accept()
        self.student_connections[student_id] = websocket
        self.room_manager.join_room(session_id, websocket)
        self.stats["connections_total"] += 1
        
        await self._send_to_socket(websocket, {
            "type": "connection",
            "status": "connected",
            "role": "student",
            "student_id": student_id,
            "timestamp": datetime.utcnow().isoformat(),
        })
        
        # Broadcast student joined event
        await self.broadcast_event(
            EventType.STUDENT_JOINED,
            student_id=student_id,
            session_id=session_id,
            data={"message": f"Student {student_id} joined the session"},
            alert_level=AlertLevel.INFO
        )
        
        print(f"[WS] Student {student_id} connected to session {session_id}")
    
    def disconnect(self, websocket: WebSocket):
        """Handle disconnection from any pool"""
        # Remove from dashboard
        self.dashboard_connections.discard(websocket)
        
        # Remove from proctors
        self.proctor_connections.discard(websocket)
        
        # Remove from students
        student_id = None
        session_id = None
        for sid, ws in list(self.student_connections.items()):
            if ws == websocket:
                student_id = sid
                # Try to find session_id if possible
                for sess_id, members in list(self.room_manager.rooms.items()):
                    if websocket in members:
                        session_id = sess_id
                        break
                del self.student_connections[sid]
                break
        
        # Clean up stream buffer if this was the last student connection in a room
        if session_id:
            self.extractor.cleanup(session_id)

        # Remove from all rooms
        for room_id, members in list(self.room_manager.rooms.items()):
            members.discard(websocket)
        
        if student_id:
            print(f"[WS] Student {student_id} disconnected")
        else:
            print(f"[WS] Client disconnected. Total: {self.total_connections}")
    
    async def broadcast_binary(self, session_id: str, data: bytes):
        """Broadcast binary data (video stream) to all dashboards and session proctors"""
        # 1. Forward the chunk to the AI frame extractor
        if self.extractor:
             self.extractor.add_chunk(session_id, data, self._ai_stream_callback)

        # 2. Relay raw video chunks directly to the UI
        room_members = self.room_manager.get_room_members(session_id)
        targets = (room_members & self.proctor_connections) | self.dashboard_connections
        
        disconnected = []
        for ws in targets:
            try:
                await ws.send_bytes(data)
            except Exception:
                disconnected.append(ws)
        
        for ws in disconnected:
            self.disconnect(ws)
    
    # =========================================================================
    # Event Broadcasting
    # =========================================================================
    
    async def broadcast_event(
        self,
        event_type: EventType,
        student_id: Optional[str] = None,
        session_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        alert_level: AlertLevel = AlertLevel.INFO,
    ):
        """Broadcast an event to relevant subscribers"""
        
        # Extract string values if enums were passed
        type_val = event_type.value if hasattr(event_type, "value") else event_type
        level_val = alert_level.value if hasattr(alert_level, "value") else alert_level

        event = RealtimeEvent(
            event_type=type_val,
            student_id=student_id,
            session_id=session_id,
            data=data or {},
            alert_level=level_val,
            timestamp=datetime.utcnow().isoformat(),
        )
        
        # Store in history
        self._add_to_history(event)
        
        # Prepare message
        message = json.loads(event.to_json())
        
        # Send to all dashboards
        await self._broadcast_to_set(self.dashboard_connections, message)
        
        # Send to session-specific proctors
        if session_id:
            room_members = self.room_manager.get_room_members(session_id)
            proctors_in_room = room_members & self.proctor_connections
            await self._broadcast_to_set(proctors_in_room, message)
        
        self.stats["events_sent"] += 1
        
        # Log critical alerts
        if alert_level in [AlertLevel.CRITICAL, AlertLevel.EMERGENCY]:
            self.stats["alerts_sent"] += 1
            print(f"[ALERT] {alert_level.value.upper()}: {event_type.value} - {data}")
    
    async def send_alert(
        self,
        alert_type: str,
        message: str,
        student_id: Optional[str] = None,
        session_id: Optional[str] = None,
        severity: AlertLevel = AlertLevel.WARNING,
        data: Optional[Dict[str, Any]] = None
    ):
        """Send an alert to dashboards and proctors"""
        
        alert_data = {
            "alert_type": alert_type,
            "message": message,
            **(data or {})
        }
        
        await self.broadcast_event(
            EventType.ALERT_TRIGGERED,
            student_id=student_id,
            session_id=session_id,
            data=alert_data,
            alert_level=severity
        )
    
    async def send_to_student(self, student_id: str, message: Dict[str, Any]):
        """Send a message directly to a specific student"""
        if student_id in self.student_connections:
            await self._send_to_socket(
                self.student_connections[student_id],
                message
            )
    
    async def broadcast_to_session(self, session_id: str, message: Dict[str, Any]):
        """Broadcast to all connections in a session room"""
        room_members = self.room_manager.get_room_members(session_id)
        print(f"[WS] Broadcasting to session {session_id}: {len(room_members)} members")
        await self._broadcast_to_set(room_members, message)
    
    # =========================================================================
    # Convenience Methods for Common Events
    # =========================================================================
    
    async def notify_face_missing(self, student_id: str, session_id: str, duration_seconds: int):
        """Alert when face is not detected"""
        severity = AlertLevel.WARNING if duration_seconds < 30 else AlertLevel.CRITICAL
        
        await self.broadcast_event(
            EventType.FACE_MISSING,
            student_id=student_id,
            session_id=session_id,
            data={
                "duration_seconds": duration_seconds,
                "message": f"Face not detected for {duration_seconds}s"
            },
            alert_level=severity
        )
    
    async def notify_suspicious_activity(
        self,
        student_id: str,
        session_id: str,
        activity_type: str,
        details: str
    ):
        """Alert for suspicious activity"""
        await self.broadcast_event(
            EventType.UNUSUAL_BEHAVIOR,
            student_id=student_id,
            session_id=session_id,
            data={
                "activity_type": activity_type,
                "details": details
            },
            alert_level=AlertLevel.WARNING
        )
    
    async def notify_plagiarism(
        self,
        student_id: str,
        session_id: str,
        similarity_score: float,
        matched_source: Optional[str] = None
    ):
        """Alert for potential plagiarism"""
        severity = AlertLevel.WARNING if similarity_score < 0.8 else AlertLevel.CRITICAL
        
        await self.broadcast_event(
            EventType.PLAGIARISM_DETECTED,
            student_id=student_id,
            session_id=session_id,
            data={
                "similarity_score": similarity_score,
                "matched_source": matched_source,
                "message": f"High similarity detected: {similarity_score:.1%}"
            },
            alert_level=severity
        )
    
    async def notify_behavior_violation(self, student_id: str, session_id: str, violation_type: str, details: str):
        """Notify of behavioral anomaly (Layer 2/3)"""
        await self.broadcast_event(
            EventType.BEHAVIOR_VIOLATION,
            student_id=student_id,
            session_id=session_id,
            data={"violation_type": violation_type, "details": details},
            alert_level=AlertLevel.CRITICAL
        )

    async def notify_network_change(self, student_id: str, session_id: str, old_ip: str, new_ip: str):
        """Notify of mid-session IP change (Layer 4)"""
        await self.broadcast_event(
            EventType.NETWORK_CHANGE,
            student_id=student_id,
            session_id=session_id,
            data={"old_ip": old_ip, "new_ip": new_ip, "message": "Network switch detected mid-session"},
            alert_level=AlertLevel.WARNING
        )

    async def notify_question_leak(self, student_id: str, session_id: str, url: str):
        """Notify of potential exam question leak (Layer 1)"""
        await self.broadcast_event(
            EventType.QUESTION_LEAK,
            student_id=student_id,
            session_id=session_id,
            data={"url": url, "message": "Exam question detected in browser history/search"},
            alert_level=AlertLevel.CRITICAL
        )
    
    async def notify_risk_update(
        self,
        student_id: str,
        session_id: str,
        risk_score: float,
        risk_level: str,
        factors: List[str]
    ):
        """Update risk score for a student"""
        severity = AlertLevel.INFO
        if risk_level == "high":
            severity = AlertLevel.WARNING
        elif risk_level == "critical":
            severity = AlertLevel.CRITICAL
        
        await self.broadcast_event(
            EventType.RISK_SCORE_UPDATE,
            student_id=student_id,
            session_id=session_id,
            data={
                "risk_score": risk_score,
                "risk_level": risk_level,
                "factors": factors
            },
            alert_level=severity
        )
    
    # =========================================================================
    # Heartbeat & Monitoring
    # =========================================================================
    
    async def start_heartbeat(self, interval: int = 30):
        """Start sending heartbeats to all connections"""
        while True:
            await asyncio.sleep(interval)
            await self._send_heartbeat()
    
    async def _send_heartbeat(self):
        """Send heartbeat to all connections"""
        message = {
            "type": EventType.HEARTBEAT.value,
            "timestamp": datetime.utcnow().isoformat(),
            "stats": {
                "dashboard_connections": len(self.dashboard_connections),
                "proctor_connections": len(self.proctor_connections),
                "student_connections": len(self.student_connections),
                "total_events": self.stats["events_sent"],
                "total_alerts": self.stats["alerts_sent"],
            }
        }
        
        await self._broadcast_to_set(self.dashboard_connections, message)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get monitoring statistics"""
        return {
            "connections": {
                "dashboards": len(self.dashboard_connections),
                "proctors": len(self.proctor_connections),
                "students": len(self.student_connections),
                "total": self.total_connections,
            },
            "events": {
                "sent": self.stats["events_sent"],
                "alerts": self.stats["alerts_sent"],
                "history_size": len(self.event_history),
            },
            "rooms": list(self.room_manager.rooms.keys()),
        }
    
    # =========================================================================
    # Internal Helpers
    # =========================================================================
    
    async def _send_to_socket(self, websocket: WebSocket, message: Dict[str, Any]):
        """Send message to a single socket with error handling"""
        try:
            await websocket.send_json(message)
        except Exception:
            self.disconnect(websocket)
    
    async def _broadcast_to_set(self, connections: Set[WebSocket], message: Dict[str, Any]):
        """Broadcast to a set of connections"""
        disconnected = []
        
        for ws in list(connections):
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.append(ws)
        
        # Clean up
        for ws in disconnected:
            self.disconnect(ws)

    async def broadcast_binary(self, session_id: str, data: bytes):
        """Broadcast binary data (video stream) to all dashboards and session proctors"""
        room_members = self.room_manager.get_room_members(session_id)
        # Dashboard connections are global, proctors/students are room-specific
        targets = (room_members & self.proctor_connections) | self.dashboard_connections
        
        disconnected = []
        for ws in list(targets):
            try:
                # Binary send
                await ws.send_bytes(data)
            except Exception:
                disconnected.append(ws)
        
        for ws in disconnected:
            self.disconnect(ws)
    
    def _add_to_history(self, event: RealtimeEvent):
        """Add event to history, maintaining max size"""
        self.event_history.append(event)
        if len(self.event_history) > self.max_history:
            self.event_history = self.event_history[-self.max_history:]
    
    async def _send_history(self, websocket: WebSocket, limit: int = 20):
        """Send recent event history to a new connection"""
        recent = self.event_history[-limit:]
        for event in recent:
            await self._send_to_socket(websocket, json.loads(event.to_json()))


# Global instance
_realtime_manager: Optional[RealtimeMonitoringManager] = None


def get_realtime_manager() -> RealtimeMonitoringManager:
    """Get or create the global realtime manager"""
    global _realtime_manager
    if _realtime_manager is None:
        _realtime_manager = RealtimeMonitoringManager()
    return _realtime_manager
