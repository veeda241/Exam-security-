"""
ExamGuard Pro V2 API package.

Flat route modules (blueprint layout):
  auth.py, exams.py, sessions.py, events.py, reports.py, ws.py

Legacy V1 code remains under api/endpoints/, api/schemas/, etc.
"""
from api.router_v2 import api_router

__all__ = ["api_router"]
