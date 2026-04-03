import os
import sys

# Ensure the server directory is on sys.path so bare imports (api, config, auth, services) work
# regardless of whether we're launched via 'uvicorn server.main:app' or 'python main.py'
_server_dir = os.path.dirname(os.path.abspath(__file__))
if _server_dir not in sys.path:
    sys.path.insert(0, _server_dir)

# Critical: Set matplotlib backend to Agg to avoid font cache issues and X11 errors on headless servers
os.environ["MPLBACKEND"] = "Agg"
os.environ["MPLCONFIGDIR"] = "/tmp/matplotlib_cache"

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from typing import List, Optional
import uvicorn
import asyncio
import mimetypes

# Fix mime types for .js and .css files
mimetypes.add_type('application/javascript', '.js')
mimetypes.add_type('text/css', '.css')

# Remove unused imports
from api import register_all_routers, get_router_info
from services.face_detection import SecureVision

# Discovery of React Build Directory
possible_dist_dirs = [
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "examguard-pro", "dist"),
    os.path.join(os.getcwd(), "examguard-pro", "dist"),
    os.path.join(os.path.dirname(__file__), "dist")
]

REACT_BUILD_DIR = None
for dist_dir in possible_dist_dirs:
    if os.path.exists(dist_dir) and os.path.isfile(os.path.join(dist_dir, "index.html")):
        REACT_BUILD_DIR = dist_dir
        print(f"[INFO] Mounting ExamGuard-Pro dashboard from: {REACT_BUILD_DIR}")
        break
from services.realtime import (
    get_realtime_manager,
    RealtimeMonitoringManager,
    EventType,
    AlertLevel
)

# Authentication
from auth import auth_router

# =============================================================================
# WebSocket Connection Manager (Legacy - for backward compatibility)
# =============================================================================
class ConnectionManager:
    """Legacy connection manager - wraps RealtimeMonitoringManager"""
    
    def __init__(self):
        self._realtime = get_realtime_manager()

    async def connect(self, websocket: WebSocket):
        await self._realtime.connect_dashboard(websocket)

    def disconnect(self, websocket: WebSocket):
        self._realtime.disconnect(websocket)

    async def broadcast(self, message: str):
        """Send message to all connected clients"""
        import json
        try:
            data = json.loads(message)
        except:
            data = {"message": message}
        
        from services.realtime import EventType, AlertLevel
        await self._realtime.broadcast_event(
            EventType.ALERT_TRIGGERED,
            data=data,
            alert_level=AlertLevel.INFO
        )

    async def send_alert(self, alert_type: str, data: dict):
        """Send typed alert to all clients"""
        await self._realtime.send_alert(
            alert_type=alert_type,
            message=data.get("message", ""),
            data=data
        )
    
    @property
    def active_connections(self) -> List[WebSocket]:
        """For backward compatibility"""
        return list(self._realtime.dashboard_connections)


# Global connection manager
manager = ConnectionManager()


# =============================================================================
# Application Lifespan
# =============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle app startup and shutdown events"""
    # ===== STARTUP =====
    print("=" * 50)
    print("ExamGuard Pro API - Starting (Supabase Mode)...")
    print("=" * 50)
    
    # Initialize Vision Engine and store in app state
    app.state.vision_engine = SecureVision()
    
    # Initialize Advanced Gaze Analysis Service
    from services.gaze_tracking import get_gaze_service
    app.state.gaze_service = get_gaze_service()
    
    # Store connection manager in app state for access from routes
    app.state.ws_manager = manager
    app.state.realtime = get_realtime_manager()
    
    # Start the real-time analysis pipeline
    from services.pipeline import get_pipeline
    pipeline = get_pipeline()
    await pipeline.start()
    app.state.pipeline = pipeline
    
    # Start heartbeat task (20s interval to keep Render WebSockets alive)
    heartbeat_task = asyncio.create_task(
        app.state.realtime.start_heartbeat(interval=20)
    )
    
    # Log registered routers
    print("\nRegistered API Routes:")
    for router_info in get_router_info():
        print(f"  {router_info['prefix']} - {router_info['tags']}")
    
    print("\n" + "=" * 50)
    print("ExamGuard Pro API started successfully!")
    print("Real-time monitoring enabled")
    print("=" * 50 + "\n")
    
    yield
    
    # ===== SHUTDOWN =====
    heartbeat_task.cancel()
    try:
        await heartbeat_task
    except asyncio.CancelledError:
        pass
    
    # Stop the analysis pipeline
    from services.pipeline import get_pipeline
    await get_pipeline().stop()
    
    print("\n" + "=" * 50)
    print("ExamGuard Pro API shutting down...")
    print("=" * 50)


# =============================================================================
# Create FastAPI Application
# =============================================================================
app = FastAPI(
    title="ExamGuard Pro API",
    description="""
    ## Exam Proctoring Backend (Supabase Managed)
    
    AI-powered exam monitoring with:
    - 👤 Face detection & engagement tracking
    - 📸 Screenshot OCR analysis
    - 📝 Text similarity & plagiarism detection
    - 🤖 Transformer-based NLP analysis
    - 📊 Real-time risk scoring
    """,
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    redirect_slashes=True,
)


# =============================================================================
# Middleware Configuration
# =============================================================================
from config import CORS_ORIGINS
from typing import List

# Type-safe CORS handling
origins: List[str] = []
if isinstance(CORS_ORIGINS, str):
    if CORS_ORIGINS == "*":
        origins = ["*"]
    else:
        origins = [o.strip() for o in CORS_ORIGINS.split(",")]
elif isinstance(CORS_ORIGINS, list):
    origins = [str(o) for o in CORS_ORIGINS]
else:
    origins = []

# Ensure wildcard and dev origins are handled
if "*" not in origins:
    dev_origins = ["http://localhost:3000", "http://localhost:5173"]
    for o in dev_origins:
        if o not in origins:
            origins.append(o)
    # Always include wildcard for extension support in this environment
    origins.append("*")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if "*" in origins else origins,
    allow_credentials=True if "*" not in origins else False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Root Endpoints
# =============================================================================
@app.get("/api/health-check", tags=["Root"])
async def root():
    """Welcome message and health check (JSON)"""
    return {
        "status": "online",
        "service": "ExamGuard Pro Headless API",
        "version": "2.0.0",
        "dashboard": "/",
        "docs": "/docs"
    }

# =============================================================================
# Register API Routers
# =============================================================================

# Always include Authentication router
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])

# Register all other API routers from the api/ folder
register_all_routers(app)
# WebSocket Endpoints - Real-Time Monitoring
# =============================================================================

@app.websocket("/ws/alerts")
@app.websocket("/ws/alerts/")
async def websocket_alerts(websocket: WebSocket):
    """
    WebSocket endpoint for real-time alerts to dashboard.
    Legacy endpoint - maintains backward compatibility.
    """
    print(f"[WS] Dashboard client connecting to legacy alerts...")
    try:
        await manager.connect(websocket)
        from starlette.websockets import WebSocketState
        if websocket.application_state != WebSocketState.CONNECTED:
            return

        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except (WebSocketDisconnect, RuntimeError, Exception) as e:
        print(f"[WS] Dashboard legacy error: {e}")
        manager.disconnect(websocket)


@app.websocket("/ws/dashboard")
@app.websocket("/ws/dashboard/")
async def websocket_dashboard(websocket: WebSocket):
    """
    WebSocket endpoint for dashboard real-time updates.
    Receives all events across all sessions.
    """
    print(f"[WS] Dashboard client connecting...")
    realtime = get_realtime_manager()
    
    try:
        # Explicit connect with state check
        await realtime.connect_dashboard(websocket)
        
        # Guard: Ensure we are actually connected before loop
        from starlette.websockets import WebSocketState
        if websocket.application_state != WebSocketState.CONNECTED:
            print("[WS] Dashboard connection check failed - closing")
            return

        import datetime
        while True:
            data = await websocket.receive_text()
            
            # Handle commands from dashboard
            if data == "ping":
                await websocket.send_json({"type": "pong", "timestamp": datetime.datetime.utcnow().isoformat()})
            elif data == "stats":
                await websocket.send_json({"type": "stats", "data": realtime.get_stats()})
            elif data.startswith("subscribe:"):
                # Subscribe to specific session
                session_id = data.split(":", 1)[1]
                realtime.room_manager.join_room(session_id, websocket)
                await websocket.send_json({"type": "subscribed", "session_id": session_id})
            elif data.startswith("command:"):
                # Dashboard can send commands to students (via broadcast_to_session)
                import json
                try:
                    cmd_data = json.loads(data.split(":", 1)[1])
                    # Try to get session_id or student_id as routing key
                    routing_id = cmd_data.get("session_id") or cmd_data.get("student_id")
                    if routing_id and routing_id != "undefined":
                        await realtime.broadcast_to_session(routing_id, cmd_data)
                        print(f"[WS] Dashboard command broadcasted to session: {routing_id}")
                    else:
                        print(f"[WS] Dashboard command missing routing ID: {cmd_data}")
                except Exception as e:
                    print(f"[WS] Dashboard command error: {e}")
            elif data.startswith("webrtc:"):
                # Route WebRTC signaling from dashboard to student
                import json
                try:
                    payload = json.loads(data.split(":", 1)[1])
                    target_student = payload.get("target")
                    signal_type = payload.get('sdp', {}).get('type', 'ICE') if payload.get('sdp') else 'ICE'
                    print(f"[WS] Dashboard WebRTC signal: {signal_type} -> target: {target_student}")
                    if target_student:
                        ws_student = realtime.student_connections.get(target_student)
                        if ws_student:
                            print(f"[WS] Found student connection for {target_student}, sending signal")
                            await realtime._send_to_socket(ws_student, {
                                "type": "webrtc_signal",
                                "from": "dashboard",
                                "payload": payload
                            })
                        else:
                            print(f"[WS] Student connection NOT FOUND for {target_student}. Available: {list(realtime.student_connections.keys())}")
                except Exception as e:
                    print(f"[WS] Dashboard WebRTC routing error: {e}")
                
    except (WebSocketDisconnect, RuntimeError, Exception) as e:
        print(f"[WS] Dashboard error: {e}")
        realtime.disconnect(websocket)


@app.websocket("/ws/proctor/{session_id}")
@app.websocket("/ws/proctor/{session_id}/")
async def websocket_proctor(
    websocket: WebSocket,
    session_id: str
):
    """
    WebSocket endpoint for proctors monitoring a specific session.
    Receives events only for the specified session.
    """
    try:
        print(f"[WS] Proctor client connecting to session: {session_id}")
        realtime = get_realtime_manager()
        await realtime.connect_proctor(websocket, session_id)
        
        from starlette.websockets import WebSocketState
        if websocket.application_state != WebSocketState.CONNECTED:
            return

        while True:
            data = await websocket.receive_text()
            
            if data == "ping":
                await websocket.send_json({"type": "pong"})
            elif data.startswith("alert:"):
                # Proctor can send alerts to students
                import json
                try:
                    alert_data = json.loads(data.split(":", 1)[1])
                    await realtime.broadcast_to_session(session_id, {
                        "type": "proctor_alert",
                        "data": alert_data
                    })
                except:
                    pass
            elif data.startswith("command:"):
                # Proctor can send commands to students (e.g. shutdown)
                import json
                try:
                    cmd_data = json.loads(data.split(":", 1)[1])
                    await realtime.broadcast_to_session(session_id, cmd_data)
                except:
                    pass
                    
    except (WebSocketDisconnect, RuntimeError, Exception) as e:
        print(f"[WS] Proctor error (session {session_id}): {e}")
        realtime.disconnect(websocket)


@app.websocket("/ws/student")
@app.websocket("/ws/student/")
@app.websocket("/ws/student/{student_id}")
@app.websocket("/ws/student/{student_id}/")
async def websocket_student(
    websocket: WebSocket,
    student_id: Optional[str] = None,
    session_id: Optional[str] = Query(None)
):
    """
    WebSocket endpoint for students.
    Receives alerts and instructions from proctors.
    """
    try:
        # Still none? Try to get from query params manually
        if not student_id:
            student_id = websocket.query_params.get("student_id", "unknown")

        print(f"[WS] Incoming student connection: {student_id} (Session: {session_id})")
        realtime = get_realtime_manager()
        await realtime.connect_student(websocket, student_id, session_id or "default")
        
        from starlette.websockets import WebSocketState
        if websocket.application_state != WebSocketState.CONNECTED:
            return

        while True:
            # Use general receive to handle both text and bytes
            message = await websocket.receive()
            
            if "text" in message:
                data = message["text"]
                if data == "ping":
                    await websocket.send_json({"type": "pong"})
                elif data.startswith("event:"):
                    # Student reporting an event
                    import json
                    try:
                        event_data = json.loads(data.split(":", 1)[1])
                        event_type = event_data.get("type", "unknown")
                        
                        # Map to EventType
                        event_map = {
                            "tab_switch": EventType.TAB_SWITCH,
                            "copy": EventType.COPY_PASTE,
                            "paste": EventType.COPY_PASTE,
                            "blur": EventType.WINDOW_BLUR,
                        }
                        
                        if event_type in event_map:
                            await realtime.broadcast_event(
                                event_map[event_type],
                                student_id=student_id,
                                session_id=session_id,
                                data=event_data,
                                alert_level=AlertLevel.WARNING
                            )
                    except:
                        pass
                elif data.startswith("webrtc:"):
                    # Route WebRTC signaling from student to dashboards monitoring this session's exam_id
                    import json
                    try:
                        payload = json.loads(data.split(":", 1)[1])
                        signal_type = payload.get('sdp', {}).get('type', 'ICE') if payload.get('sdp') else 'ICE'
                        print(f"[WS] Student {student_id} WebRTC signal: {signal_type} -> session {session_id}")
                        # Broadcast signal to the session_id room (dashboard listens here)
                        await realtime.broadcast_to_session(session_id, {
                            "type": "webrtc_signal",
                            "student_id": student_id,
                            "payload": payload
                        })
                    except Exception as e:
                        print(f"[WS] Student WebRTC routing error: {e}")
            
            elif "bytes" in message:
                # Live streaming chunks (MediaRecorder)
                if session_id:
                    await realtime.broadcast_binary(session_id, message["bytes"])
                    
    except (WebSocketDisconnect, RuntimeError, Exception) as e:
        print(f"[WS] Student error ({student_id}): {e}")
        realtime.disconnect(websocket)
        
        # Broadcast student left event
        try:
            await realtime.broadcast_event(
                EventType.STUDENT_LEFT,
                student_id=student_id,
                session_id=session_id,
                data={"message": f"Student {student_id} disconnected"},
                alert_level=AlertLevel.INFO
            )
            
            # Update database to mark session as ended
            if session_id and session_id != "default":
                from supabase_client import get_supabase
                import datetime
                
                # Fetch current session to preserve risk score
                supabase = get_supabase()
                res = supabase.table("exam_sessions").select("risk_score, risk_level").eq("id", session_id).execute()
                if res.data:
                    supabase.table("exam_sessions").update({
                        "is_active": False,
                        "ended_at": datetime.datetime.utcnow().isoformat()
                    }).eq("id", session_id).execute()
                    print(f"[WS] Session {session_id} marked as ended in DB")
        except Exception as update_err:
            print(f"[WS] Failed to update session status on disconnect: {update_err}")


@app.get("/ws/stats", tags=["WebSocket"])
async def websocket_stats():
    """Get WebSocket connection statistics"""
    realtime = get_realtime_manager()
    return realtime.get_stats()


# =============================================================================
# Static Files & Upload Directories
# =============================================================================
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
SCREENSHOTS_DIR = os.path.join(UPLOAD_DIR, "screenshots")
WEBCAM_DIR = os.path.join(UPLOAD_DIR, "webcam")
REPORTS_DIR = os.path.join(UPLOAD_DIR, "reports")

# Create directories
for directory in [SCREENSHOTS_DIR, WEBCAM_DIR, REPORTS_DIR]:
    os.makedirs(directory, exist_ok=True)

# Mount static files for uploaded content
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Mount specific folders for performance
if REACT_BUILD_DIR:
    # Mount assets folder for JS/CSS
    assets_dir = os.path.join(REACT_BUILD_DIR, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

# SPA Fallback will be registered at the end (after all other routes)

# =============================================================================
# Static Files & Upload Directories
# =============================================================================
async def root_legacy():
    """Health check endpoint (legacy path)"""
    return {
        "status": "online",
        "service": "ExamGuard Pro API",
        "version": "2.0.0",
        "docs": "/docs",
        "dashboard": "/",
    }


@app.get("/health", tags=["Root"])
async def health_check():
    """Detailed health check"""
    from services.transformer_analysis import get_transformer_analyzer
    from services.pipeline import get_pipeline
    
    transformer_status = {"available": False}
    try:
        analyzer = get_transformer_analyzer()
        transformer_status = analyzer.get_status()
    except Exception as e:
        transformer_status = {"available": False, "error": str(e)}
    
    realtime = get_realtime_manager()
    ws_stats = realtime.get_stats()
    pipeline = get_pipeline()
    
    return {
        "status": "healthy",
        "database": "supabase",
        "websocket": {
            "total_connections": ws_stats["connections"]["total"],
            "dashboards": ws_stats["connections"]["dashboards"],
            "proctors": ws_stats["connections"]["proctors"],
            "students": ws_stats["connections"]["students"],
            "events_sent": ws_stats["events"]["sent"],
            "active_sessions": len(ws_stats["rooms"]),
        },
        "pipeline": pipeline.get_stats(),
        "ai_modules": {
            "face_detection": "ready",
            "ocr": "ready",
            "text_similarity": "ready",
            "anomaly_detection": "ready",
            "transformer": transformer_status,
        }
    }


@app.get("/api/pipeline/stats", tags=["Pipeline"])
async def pipeline_stats():
    """Get real-time analysis pipeline statistics"""
    from services.pipeline import get_pipeline
    return get_pipeline().get_stats()


@app.get("/api", tags=["Root"])
async def api_info():
    """Get API information and available endpoints"""
    return {
        "name": "ExamGuard Pro API",
        "version": "2.0.0",
        "endpoints": get_router_info(),
        "documentation": {
            "swagger": "/docs",
            "redoc": "/redoc",
        }
    }


# =============================================================================
# SPA Fallback for React Router (MUST be last route)
# =============================================================================
@app.get("/{full_path:path}", include_in_schema=False)
async def spa_fallback(request: Request, full_path: str):
    """Serve files if they exist, else serve index.html (SPA support)"""
    if not REACT_BUILD_DIR:
        return {"detail": "Dashboard not built"}
        
    # 1. Check API / System prefixes - ignore these
    if any(full_path.startswith(p) for p in ("api/", "docs", "redoc", "ws/", "uploads/")):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Not Found")
    
    # 2. Check if the literal file exists in the build dir (e.g., favicon.ico)
    potential_file = os.path.join(REACT_BUILD_DIR, full_path)
    if os.path.isfile(potential_file):
        from fastapi.responses import FileResponse
        return FileResponse(potential_file)
        
    # 3. Fallback to index.html for any other route (React Router)
    index_path = os.path.join(REACT_BUILD_DIR, "index.html")
    if os.path.exists(index_path):
        from fastapi.responses import FileResponse
        return FileResponse(index_path)
    
    return {"detail": "Index file not found"}


# =============================================================================
# Run Server
# =============================================================================
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
