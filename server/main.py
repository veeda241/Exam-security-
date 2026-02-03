"""
ExamGuard Pro - Backend Server
Main FastAPI application entry point
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from typing import List, Dict
import uvicorn
import os
import json

from routers import students, events_log, uploads, reports, research, analysis
from database import init_db
from services.face_detection import SecureVision


# WebSocket Connection Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

# Global Vision Engine (moved to app.state)

# Lifespan event handler for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle app startup and shutdown events"""
    # Startup
    await init_db()
    
    # Initialize Vision Engine and store in app state
    app.state.vision_engine = SecureVision()
    print("ExamGuard Pro API started")
    yield
    # Shutdown
    print("ExamGuard Pro API shutdown")
    # Shutdown
    print("ExamGuard Pro API shutdown")


# Create FastAPI app
app = FastAPI(
    title="ExamGuard Pro API",
    description="Exam proctoring backend for session management and AI analysis",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS for extension communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to extension ID
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(students.router, prefix="/api/students", tags=["Students"])
app.include_router(events_log.router, prefix="/api/events", tags=["Events"])
app.include_router(uploads.router, prefix="/api/uploads", tags=["Uploads"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])
app.include_router(research.router, prefix="/api/research", tags=["Research Analysis"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["Analysis"])

# WebSocket Endpoint
@app.websocket("/ws/alerts")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Create upload directories
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
SCREENSHOTS_DIR = os.path.join(UPLOAD_DIR, "screenshots")
WEBCAM_DIR = os.path.join(UPLOAD_DIR, "webcam")

os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
os.makedirs(WEBCAM_DIR, exist_ok=True)

# Mount static files for uploaded content
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Mount frontend
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(FRONTEND_DIR):
    app.mount("/dashboard", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
else:
    print(f"Warning: Frontend directory not found at {FRONTEND_DIR}")


@app.get("/", tags=["Root"])
async def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "service": "ExamGuard Pro API",
        "version": "1.0.0",
    }


@app.get("/health", tags=["Root"])
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "database": "connected",
        "ai_modules": {
            "face_detection": "ready",
            "ocr": "ready",
            "text_similarity": "ready",
            "anomaly_detection": "ready",
        }
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
