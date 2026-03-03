"""
ExamGuard Pro - API Models Package
Re-exports SQLAlchemy models from the main models package
"""

# Import from the existing models package to avoid duplication
from models.student import Student
from models.session import ExamSession
from models.event import Event
from models.analysis import AnalysisResult

# Try to import research models (may not exist in original)
try:
    from models.research import ResearchJourney, SearchStrategy
except ImportError:
    ResearchJourney = None
    SearchStrategy = None

__all__ = [
    "Student",
    "ExamSession", 
    "Event",
    "AnalysisResult",
    "ResearchJourney",
    "SearchStrategy"
]
