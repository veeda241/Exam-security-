"""
ExamGuard Pro - Configuration
Application settings and environment variables
"""

import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "uploads"
SCREENSHOTS_DIR = UPLOAD_DIR / "screenshots"
WEBCAM_DIR = UPLOAD_DIR / "webcam"

# Database configuration
# The user requested PostgreSQL support
PG_USER = os.getenv("PG_USER", "postgres")
PG_PASSWORD = os.getenv("PG_PASSWORD", "password")
PG_HOST = os.getenv("PG_HOST", "localhost")
PG_PORT = os.getenv("PG_PORT", "5432")
PG_DB = os.getenv("PG_DB", "examguard")

DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    f"postgresql+asyncpg://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_DB}"
)

# Fallback for local development if PostgreSQL is not available
if os.getenv("USE_SQLITE", "true").lower() == "true":
    DATABASE_URL = f"sqlite+aiosqlite:///{BASE_DIR}/examguard.db"

# API Configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))

# Capture settings
SCREENSHOT_INTERVAL_SECONDS = 3
WEBCAM_INTERVAL_SECONDS = 5
IMAGE_QUALITY = 0.7
MAX_IMAGE_WIDTH = 1280
MAX_IMAGE_HEIGHT = 720

# Forbidden keywords for OCR detection
FORBIDDEN_KEYWORDS = [
    "chatgpt",
    "chat.openai",
    "openai.com",
    "bard.google",
    "gemini.google",
    "stackoverflow.com",
    "stack overflow",
    "chegg.com",
    "chegg",
    "quizlet.com",
    "quizlet",
    "coursehero",
    "course hero",
    "brainly.com",
    "brainly",
    "claude.ai",
    "anthropic",
    "perplexity.ai",
    "wolframalpha",
    "symbolab",
    "photomath",
]

# Risk score weights
RISK_WEIGHTS = {
    "TAB_SWITCH": 10,
    "WINDOW_BLUR": 5,
    "FORBIDDEN_SITE": 40,
    "FORBIDDEN_CONTENT": 40,
    "FACE_ABSENT": 20,
    "COPY": 15,
    "PASTE": 10,
    "SUSPICIOUS_SHORTCUT": 15,
    "CONTEXT_MENU": 5,
    "PAGE_HIDDEN": 8,
    "SCREEN_SHARE_STOPPED": 50,
}

# Risk score thresholds
RISK_THRESHOLDS = {
    "SAFE": 30,
    "REVIEW": 60,
    "SUSPICIOUS": 100,
}

# Face detection settings
FACE_ABSENCE_THRESHOLD_SECONDS = 10
MIN_FACE_CONFIDENCE = 0.7

# AI Module settings
OCR_LANGUAGE = "eng"
TEXT_SIMILARITY_THRESHOLD = 0.75
