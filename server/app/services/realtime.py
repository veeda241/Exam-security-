import json
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, asdict
from enum import Enum
import numpy as np
from fastapi import WebSocket, WebSocketDisconnect
from loguru import logger

from app.core.config import settings

class AlertLevel(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

class EventType(str, Enum):
    SESSION_STARTED = "session_started"
    SESSION_ENDED = "session_ended"
    STUDENT_JOINED = "student_joined"
    STUDENT_LEFT = "student_left"
    FACE_DETECTED = "face_detected"
    FACE_MISSING = "face_missing"
    MULTIPLE_FACES = "multiple_faces"
    TAB_SWITCH = "tab_switch"
    COPY_PASTE = "copy_paste"
    SCREENSHOT_ATTEMPT = "screenshot_attempt"
    WINDOW_BLUR = "window_blur"
    GAZE_AVERSION = "gaze_aversion"
    MOUTH_MOVEMENT = "mouth_movement"
    BEHAVIOR_VIOLATION = "behavior_violation"
    RISK_SCORE_UPDATE = "risk_score_update"
    ALERT_TRIGGERED = "alert_triggered"
    HEARTBEAT = "heartbeat"

@dataclass
class RealtimeEvent:
    event_type: str
    student_id: Optional[str]
    session_id: Optional[str]
    data: Dict[str, Any]
    alert_level: str
    timestamp: str
    
    def to_json(self) -> str:
        return json.dumps(asdict(self))

class RoomManager:
    def __init__(self):
        self.rooms: Dict[str, Set[WebSocket]] = {}
    
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
    def __init__(self, max_history: int = 100):
        self.dashboard_connections: Set[WebSocket] = set()
        self.proctor_connections: Set[WebSocket] = set()
        self.student_connections: Dict[str, WebSocket] = {}
        self.room_manager = RoomManager()
        self.event_history: List[RealtimeEvent] = []
        self.max_history = max_history
        self.stats_data = {
            "events_sent": 0,
            "connections_total": 0,
            "alerts_sent": 0,
        }

    async def connect_dashboard(self, websocket: WebSocket):
        await websocket.accept()
        self.dashboard_connections.add(websocket)
        self.stats_data["connections_total"] += 1
        await self._send_to_socket(websocket, {
            "type": "connection",
            "status": "connected",
            "role": "dashboard",
            "timestamp": datetime.utcnow().isoformat(),
        })
        logger.info(f"Dashboard connected. Total: {len(self.dashboard_connections)}")

    async def connect_student(self, websocket: WebSocket, student_id: str, session_id: str):
        await websocket.accept()
        self.student_connections[student_id] = websocket
        self.room_manager.join_room(session_id, websocket)
        self.stats_data["connections_total"] += 1
        await self.broadcast_event(
            EventType.STUDENT_JOINED,
            student_id=student_id,
            session_id=session_id,
            data={"message": f"Student {student_id} joined"},
            alert_level=AlertLevel.INFO
        )
        logger.info(f"Student {student_id} connected to session {session_id}")

    def disconnect(self, websocket: WebSocket):
        self.dashboard_connections.discard(websocket)
        self.proctor_connections.discard(websocket)
        for sid, ws in list(self.student_connections.items()):
            if ws == websocket:
                del self.student_connections[sid]
                break
        for room_id, members in list(self.room_manager.rooms.items()):
            members.discard(websocket)

    async def broadcast_event(self, event_type: EventType, student_id: Optional[str] = None, session_id: Optional[str] = None, data: Optional[Dict[str, Any]] = None, alert_level: AlertLevel = AlertLevel.INFO):
        event = RealtimeEvent(
            event_type=event_type.value if hasattr(event_type, "value") else event_type,
            student_id=student_id,
            session_id=session_id,
            data=data or {},
            alert_level=alert_level.value if hasattr(alert_level, "value") else alert_level,
            timestamp=datetime.utcnow().isoformat(),
        )
        self.event_history.append(event)
        if len(self.event_history) > self.max_history:
            self.event_history.pop(0)
        
        message = asdict(event)
        await self._broadcast_to_set(self.dashboard_connections, message)
        if session_id:
            await self._broadcast_to_set(self.room_manager.get_room_members(session_id), message)
        self.stats_data["events_sent"] += 1

    async def _send_to_socket(self, websocket: WebSocket, message: Dict[str, Any]):
        try:
            await websocket.send_json(message)
        except Exception:
            self.disconnect(websocket)

    async def _broadcast_to_set(self, connections: Set[WebSocket], message: Dict[str, Any]):
        disconnected = []
        for ws in list(connections):
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            self.disconnect(ws)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "connections": {
                "dashboards": len(self.dashboard_connections),
                "students": len(self.student_connections),
                "total": len(self.dashboard_connections) + len(self.student_connections),
            },
            "events": self.stats_data
        }

_manager = None
def get_realtime_manager():
    global _manager
    if _manager is None:
        _manager = RealtimeMonitoringManager()
    return _manager
