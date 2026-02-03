"""
ExamGuard Pro - Services Package
AI analysis modules
"""

# Export key functions for easy access
from .face_detection import SecureVision
from .ocr import ScreenOCR
from .similarity import TextSimilarityChecker, get_checker
from .anomaly import AnomalyDetector, get_detector
from .object_detection import get_object_detector
from .llm import get_llm_service
from .transformer_analysis import TransformerAnalyzer, get_transformer_analyzer

__all__ = [
    "SecureVision",
    "ScreenOCR", 
    "TextSimilarityChecker",
    "get_checker",
    "AnomalyDetector",
    "get_detector",
    "get_object_detector",
    "get_llm_service",
    "TransformerAnalyzer",
    "get_transformer_analyzer"
]
