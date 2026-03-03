"""
ExamGuard Pro - Services Package
AI analysis modules + Local ML/Analysis Services

Uses lazy imports to avoid blocking startup with heavy ML model loading.
"""

import importlib as _importlib

__all__ = [
    # Existing services
    "SecureVision",
    "ScreenOCR",
    "TextSimilarityChecker",
    "get_checker",
    "AnomalyDetector",
    "get_detector",
    "get_object_detector",
    "get_llm_service",
    "TransformerAnalyzer",
    "get_transformer_analyzer",

    # Local ML Services
    "BiometricsService",
    "get_biometrics_service",
    "GazeAnalysisService",
    "get_gaze_service",
    "ForensicsService",
    "get_forensics_service",
    "AudioAnalysisService",
    "get_audio_service",
]

# Mapping of public name -> (submodule, attribute)
_LAZY_MAP = {
    "SecureVision":             ("face_detection",       "SecureVision"),
    "ScreenOCR":                ("ocr",                  "ScreenOCR"),
    "TextSimilarityChecker":    ("similarity",           "TextSimilarityChecker"),
    "get_checker":              ("similarity",           "get_checker"),
    "AnomalyDetector":          ("anomaly",              "AnomalyDetector"),
    "get_detector":             ("anomaly",              "get_detector"),
    "get_object_detector":      ("object_detection",     "get_object_detector"),
    "get_llm_service":          ("llm",                  "get_llm_service"),
    "TransformerAnalyzer":      ("transformer_analysis", "TransformerAnalyzer"),
    "get_transformer_analyzer": ("transformer_analysis", "get_transformer_analyzer"),
    "BiometricsService":        ("biometrics",           "BiometricsService"),
    "get_biometrics_service":   ("biometrics",           "get_biometrics_service"),
    "GazeAnalysisService":      ("gaze_tracking",        "GazeAnalysisService"),
    "get_gaze_service":         ("gaze_tracking",        "get_gaze_service"),
    "ForensicsService":         ("browser_forensics",    "ForensicsService"),
    "get_forensics_service":    ("browser_forensics",    "get_forensics_service"),
    "AudioAnalysisService":     ("audio_analysis",       "AudioAnalysisService"),
    "get_audio_service":        ("audio_analysis",       "get_audio_service"),
}


def __getattr__(name: str):
    if name in _LAZY_MAP:
        module_name, attr_name = _LAZY_MAP[name]
        module = _importlib.import_module(f".{module_name}", __name__)
        value = getattr(module, attr_name)
        # Cache in module namespace so __getattr__ is not called again
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
