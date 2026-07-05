"""ExamGuard Pro V2 — API router assembly."""
from fastapi import APIRouter

from api import auth, exams, sessions, events, reports, ws

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(exams.router, prefix="/exams", tags=["exams"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
api_router.include_router(events.router, prefix="/events", tags=["events"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(ws.router, tags=["websocket"])

__all__ = ["api_router"]
