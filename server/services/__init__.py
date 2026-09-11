"""
ExamGuard Pro - Services Package
AI analysis modules

Uses lazy imports to avoid blocking startup with heavy ML model loading.
"""

import importlib as _importlib

__all__ = [
    "SecureVision",
    "ScreenOCR",
    "get_object_detector",
    "TransformerAnalyzer",
    "get_transformer_analyzer",
    "classify_page",
    "classify_for_tracker",
]

# Mapping of public name -> (submodule, attribute)
_LAZY_MAP = {
    "SecureVision":             ("face_detection",       "SecureVision"),
    "ScreenOCR":                ("ocr",                  "ScreenOCR"),
    "get_object_detector":      ("object_detection",     "get_object_detector"),
    "TransformerAnalyzer":      ("transformer_analysis", "TransformerAnalyzer"),
    "get_transformer_analyzer": ("transformer_analysis", "get_transformer_analyzer"),
    "classify_page":            ("page_classifier",      "classify_page"),
    "classify_for_tracker":     ("page_classifier",      "classify_for_tracker"),
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
