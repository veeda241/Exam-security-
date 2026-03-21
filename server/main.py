"""
ExamGuard Pro - Backend Server
Main FastAPI application entry point

Updated to use organized API structure from api/ folder
"""

# Prevent matplotlib font cache build on startup (blocks port binding)
import os
import os
print("\n" + "#" * 80)
print("### LOADING MAIN.PY - CURRENT WORKING DIRECTORY: " + os.getcwd())
print("#" * 80 + "\n")
os.environ.setdefault("MPLBACKEND", "Agg")
from dotenv import load_dotenv
# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from typing import List, Optional
import uvicorn
import asyncio

# Remove unused imports
from api import register_all_routers, get_router_info
from services.face_detection import SecureVision
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
    
    # Store connection manager in app state for access from routes
    app.state.ws_manager = manager
    app.state.realtime = get_realtime_manager()
    
    # Start the real-time analysis pipeline
    from services.pipeline import get_pipeline
    pipeline = get_pipeline()
    await pipeline.start()
    app.state.pipeline = pipeline
    
    # Start heartbeat task
    heartbeat_task = asyncio.create_task(
        app.state.realtime.start_heartbeat(interval=30)
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
)


# =============================================================================
# Middleware Configuration
# =============================================================================
from config import CORS_ORIGINS
# Parse CORS_ORIGINS from env if it's a string
origins = []
if isinstance(CORS_ORIGINS, str):
    if CORS_ORIGINS == "*":
        origins = ["*"]
    else:
        origins = [o.strip() for o in CORS_ORIGINS.split(",")]
else:
    origins = list(CORS_ORIGINS) if CORS_ORIGINS else []

# Add default dev origins if not present
dev_origins = ["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:3000", "http://127.0.0.1:5173"]
for o in dev_origins:
    if o not in origins and "*" not in origins:
        origins.append(o)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if "*" not in origins else ["*"],
    allow_credentials=True if "*" not in origins else False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Root Endpoints
# =============================================================================
@app.get("/", tags=["Root"])
async def root():
    """Simple health check for extension connectivity"""
    return {
        "status": "online",
        "service": "ExamGuard Pro API",
        "version": "2.0.0"
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
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
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
    await realtime.connect_dashboard(websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            
            # Handle commands from dashboard
            if data == "ping":
                await websocket.send_json({"type": "pong", "timestamp": __import__('datetime').datetime.utcnow().isoformat()})
            elif data == "stats":
                await websocket.send_json({"type": "stats", "data": realtime.get_stats()})
            elif data.startswith("subscribe:"):
                # Subscribe to specific session
                session_id = data.split(":", 1)[1]
                realtime.room_manager.join_room(session_id, websocket)
                await websocket.send_json({"type": "subscribed", "session_id": session_id})
                
    except WebSocketDisconnect:
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
    print(f"[WS] Proctor client connecting to session: {session_id}")
    realtime = get_realtime_manager()
    await realtime.connect_proctor(websocket, session_id)
    
    try:
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
                    
    except WebSocketDisconnect:
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
    # Still none? Try to get from query params manually
    if not student_id:
        student_id = websocket.query_params.get("student_id", "unknown")

    print(f"[WS] Incoming student connection: {student_id} (Session: {session_id})")
    realtime = get_realtime_manager()
    await realtime.connect_student(websocket, student_id, session_id or "default")
    
    try:
        while True:
            data = await websocket.receive_text()
            
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
                    
    except WebSocketDisconnect:
        realtime.disconnect(websocket)
        
        # Broadcast student left event
        await realtime.broadcast_event(
            EventType.STUDENT_LEFT,
            student_id=student_id,
            session_id=session_id,
            data={"message": f"Student {student_id} disconnected"},
            alert_level=AlertLevel.INFO
        )


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

# Mount React frontend (monolithic deployment)
# Check multiple locations to ensure it works on Render and locally
possible_dist_dirs = [
    os.path.join(os.path.dirname(__file__), "dist"),
    os.path.join(os.getcwd(), "dist"),
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "react-frontend", "dist"),
    "/opt/render/project/src/server/dist"
]

REACT_BUILD_DIR = None
for dist_dir in possible_dist_dirs:
    if os.path.exists(dist_dir) and os.path.isfile(os.path.join(dist_dir, "index.html")):
        REACT_BUILD_DIR = dist_dir
        print(f"[INFO] Mounting React frontend from: {REACT_BUILD_DIR}")
        break

if REACT_BUILD_DIR:
    from fastapi.responses import FileResponse
    from starlette.exceptions import HTTPException as StarletteHTTPException

    # Mount static assets
    assets_dir = os.path.join(REACT_BUILD_DIR, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="react-assets")
    else:
        # SPA files might be directly in dist (Vite default is dist/assets)
        print(f"[WARN] No assets folder found in {REACT_BUILD_DIR}")

    # Serve index.html at root of domain and dashboard
    @app.get("/", include_in_schema=False)
    @app.get("/dashboard", include_in_schema=False)
    @app.get("/sessions", include_in_schema=False)
    @app.get("/students", include_in_schema=False)
    @app.get("/alerts", include_in_schema=False)
    @app.get("/reports", include_in_schema=False)
    @app.get("/analytics", include_in_schema=False)
    @app.get("/settings", include_in_schema=False)
    @app.get("/student/register", include_in_schema=False)
    @app.get("/student/{path:path}", include_in_schema=False)
    async def serve_react_pages():
        """Serve React SPA for known frontend routes"""
        return FileResponse(os.path.join(REACT_BUILD_DIR, "index.html"))

    # Custom 404 handler: serve React for unknown non-API paths
    @app.exception_handler(StarletteHTTPException)
    async def spa_fallback(request, exc):
        if exc.status_code == 404:
            path = request.url.path
            # Only serve React for non-API/non-system paths
            if not any(path.startswith(p) for p in ("/api", "/docs", "/redoc", "/openapi", "/ws", "/health", "/uploads")):
                # Check if this might be a websocket upgrade attempt on a common path
                if "upgrade" in request.headers.get("connection", "").lower() and "websocket" in request.headers.get("upgrade", "").lower():
                    print(f"[WS] 404 on WebSocket upgrade for path: {path}")
                
                index_path = os.path.join(REACT_BUILD_DIR, "index.html")
                if os.path.isfile(index_path):
                    return FileResponse(index_path)
        # For API 404s and other errors, return JSON
        from fastapi.responses import JSONResponse
        return JSONResponse({
            "detail": exc.detail,
            "path": request.url.path,
            "method": request.method
        }, status_code=exc.status_code)

    print(f"[INFO] React frontend served from {REACT_BUILD_DIR}")
else:
    print(f"[INFO] React build not found at {REACT_BUILD_DIR} - skipping SPA serving")


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
# Run Server
# =============================================================================
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
