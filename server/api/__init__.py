"""
ExamGuard Pro - API Package
Organized API structure with models, schemas, endpoints, and utilities

Structure:
    api/
    ├── __init__.py          # This file - package exports
    ├── router.py            # Router registration helper
    ├── dependencies.py      # Shared FastAPI dependencies
    ├── utils.py             # Utility functions
    ├── models/              # SQLAlchemy database models
    │   ├── student.py
    │   ├── session.py
    │   ├── event.py
    │   ├── analysis.py
    │   └── research.py
    ├── schemas/             # Pydantic request/response schemas
    │   ├── student.py
    │   ├── session.py
    │   ├── event.py
    │   ├── analysis.py
    │   ├── report.py
    │   └── upload.py
    └── endpoints/           # FastAPI route handlers
        ├── students.py
        ├── sessions.py
        ├── events.py
        ├── analysis.py
        ├── uploads.py
        ├── reports.py
        ├── research.py
        └── transformer.py
"""

from . import models
from . import schemas
from . import endpoints
from . import dependencies
from . import utils
from .router import register_all_routers, get_router_info

__all__ = [
    "models",
    "schemas", 
    "endpoints",
    "dependencies",
    "utils",
    "register_all_routers",
    "get_router_info"
]
