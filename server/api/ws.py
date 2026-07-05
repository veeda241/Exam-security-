"""WebSocket hub."""
from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger

router = APIRouter()

_connections: dict[str, set[WebSocket]] = {}
_lock = asyncio.Lock()


async def _register(session_id: str, ws: WebSocket) -> None:
    async with _lock:
        _connections.setdefault(session_id, set()).add(ws)


async def _unregister(session_id: str, ws: WebSocket) -> None:
    async with _lock:
        if session_id in _connections:
            _connections[session_id].discard(ws)
            if not _connections[session_id]:
                del _connections[session_id]


async def _broadcast(session_id: str, message: dict[str, Any]) -> None:
    async with _lock:
        targets = list(_connections.get(session_id, set()))
    for ws in targets:
        try:
            await ws.send_json(message)
        except Exception:
            await _unregister(session_id, ws)


@router.websocket("/ws")
async def websocket_hub(websocket: WebSocket):
    await websocket.accept()
    subscribed: set[str] = set()

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                if raw == "ping":
                    await websocket.send_json({"type": "pong"})
                continue

            msg_type = msg.get("type")
            if msg_type == "subscribe":
                session_id = msg.get("session_id")
                if session_id:
                    subscribed.add(session_id)
                    await _register(session_id, websocket)
                    await websocket.send_json({
                        "type": "session_status",
                        "session_id": session_id,
                        "status": "subscribed",
                    })
            elif msg_type == "unsubscribe":
                session_id = msg.get("session_id")
                if session_id and session_id in subscribed:
                    subscribed.discard(session_id)
                    await _unregister(session_id, websocket)
            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    finally:
        for sid in subscribed:
            await _unregister(sid, websocket)
        logger.info("WebSocket client disconnected")


def setup_ws_bus_listener() -> None:
    from core.event_bus import get_event_bus

    bus = get_event_bus()

    async def handler(session_id: str, data: dict[str, Any]) -> None:
        await _broadcast(session_id, data)

    bus.subscribe(lambda sid, data: asyncio.create_task(handler(sid, data)))
