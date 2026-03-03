"""
ExamGuard Pro - Backend Server
Main FastAPI application entry point

Updated to use organized API structure from api/ folder
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from typing import List, Optional
import uvicorn
import asyncio
import os

from database import init_db
from services.face_detection import SecureVision
from services.realtime import (
    get_realtime_manager,
    RealtimeMonitoringManager,
    EventType,
    AlertLevel
)

# Authentication
from auth import auth_router

# Legacy imports (these work and are battle-tested)
from routers import students, events_log, uploads, reports, research, analysis, sessions

# Try to import new API structure (optional - for gradual migration)
NEW_API_AVAILABLE = False
try:
    from api import register_all_routers, get_router_info
    NEW_API_AVAILABLE = True
except ImportError as e:
    print(f"[INFO] New API structure not available: {e}")
    register_all_routers = None
    get_router_info = lambda: []


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
    print("ExamGuard Pro API - Starting...")
    print("=" * 50)
    
    # Initialize database
    await init_db()
    
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
    ## Exam Proctoring Backend
    
    AI-powered exam monitoring with:
    - 👤 Face detection & engagement tracking
    - 📸 Screenshot OCR analysis
    - 📝 Text similarity & plagiarism detection
    - 🤖 Transformer-based NLP analysis
    - 📊 Real-time risk scoring
    
    ### API Structure
    - `/api/students` - Student management
    - `/api/sessions` - Exam session control
    - `/api/events` - Event logging
    - `/api/analysis` - AI analysis
    - `/api/transformer` - Transformer NLP
    - `/api/uploads` - File uploads
    - `/api/reports` - Report generation
    - `/api/research` - Research journey tracking
    """,
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# =============================================================================
# Middleware Configuration
# =============================================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Register API Routers
# =============================================================================

# New organized API structure (from api/ folder) - optional
if NEW_API_AVAILABLE and register_all_routers:
    try:
        register_all_routers(app)
        print("[INFO] New API structure registered successfully")
    except Exception as e:
        print(f"[WARN] Could not register new API: {e}")

# Core routers (battle-tested, always available)
app.include_router(students.router, prefix="/api/students", tags=["Students"])
app.include_router(events_log.router, prefix="/api/events", tags=["Events"])
app.include_router(uploads.router, prefix="/api/uploads", tags=["Uploads"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])
app.include_router(research.router, prefix="/api/research", tags=["Research"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["Analysis"])
app.include_router(sessions.router, prefix="/api/sessions", tags=["Sessions"])

# Authentication router
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])

# Advanced Analytics router (100% local ML services)
try:
    from api.analytics import router as analytics_router
    app.include_router(analytics_router)  # Already has /api/analytics prefix
    print("[INFO] Advanced Analytics API registered (biometrics, gaze, forensics, audio)")
except ImportError as e:
    print(f"[WARN] Advanced Analytics not available: {e}")

# =============================================================================
# WebSocket Endpoints - Real-Time Monitoring
# =============================================================================

@app.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    """
    WebSocket endpoint for real-time alerts to dashboard.
    Legacy endpoint - maintains backward compatibility.
    """
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.websocket("/ws/dashboard")
async def websocket_dashboard(websocket: WebSocket):
    """
    WebSocket endpoint for dashboard real-time updates.
    Receives all events across all sessions.
    """
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
async def websocket_proctor(
    websocket: WebSocket,
    session_id: str
):
    """
    WebSocket endpoint for proctors monitoring a specific session.
    Receives events only for the specified session.
    """
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


@app.websocket("/ws/student/{student_id}")
async def websocket_student(
    websocket: WebSocket,
    student_id: str,
    session_id: Optional[str] = Query(None)
):
    """
    WebSocket endpoint for students.
    Receives alerts and instructions from proctors.
    """
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

# Mount frontend dashboard
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(FRONTEND_DIR):
    app.mount("/dashboard", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
else:
    print(f"[WARN] Frontend directory not found at {FRONTEND_DIR}")


# =============================================================================
# Root Endpoints
# =============================================================================
@app.get("/", tags=["Root"])
async def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "service": "ExamGuard Pro API",
        "version": "2.0.0",
        "docs": "/docs",
        "dashboard": "/dashboard",
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
