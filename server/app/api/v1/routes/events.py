from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger
from app.services.realtime import get_realtime_manager

router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    realtime = get_realtime_manager()
    await realtime.connect_dashboard(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming data if needed
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        realtime.disconnect(websocket)
        logger.info("Dashboard WebSocket disconnected")
