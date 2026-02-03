"""
ExamGuard Pro - API Endpoints Package
FastAPI route handlers organized by domain
"""

from .students import router as students_router
from .sessions import router as sessions_router
from .events import router as events_router
from .analysis import router as analysis_router
from .uploads import router as uploads_router
from .reports import router as reports_router
from .research import router as research_router
from .transformer import router as transformer_router

__all__ = [
    "students_router",
    "sessions_router",
    "events_router", 
    "analysis_router",
    "uploads_router",
    "reports_router",
    "research_router",
    "transformer_router"
]

# Router configurations for easy registration
ROUTERS = [
    {"router": students_router, "prefix": "/api/students", "tags": ["Students"]},
    {"router": sessions_router, "prefix": "/api/sessions", "tags": ["Sessions"]},
    {"router": events_router, "prefix": "/api/events", "tags": ["Events"]},
    {"router": analysis_router, "prefix": "/api/analysis", "tags": ["Analysis"]},
    {"router": uploads_router, "prefix": "/api/uploads", "tags": ["Uploads"]},
    {"router": reports_router, "prefix": "/api/reports", "tags": ["Reports"]},
    {"router": research_router, "prefix": "/api/research", "tags": ["Research"]},
    {"router": transformer_router, "prefix": "/api/transformer", "tags": ["Transformer"]},
]
