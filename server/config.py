"""
ExamGuard Pro - Configuration
Application settings and environment variables
"""

import os
from pathlib import Path
from urllib.parse import quote_plus

# Base paths
BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "uploads"
SCREENSHOTS_DIR = UPLOAD_DIR / "screenshots"
WEBCAM_DIR = UPLOAD_DIR / "webcam"

# Database configuration - Supabase PostgreSQL
# Set these via environment variables (never hardcode secrets)
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
SUPABASE_DB_PASSWORD = os.getenv("SUPABASE_DB_PASSWORD", "")

# Supabase PostgreSQL connection (Direct connection - port 5432)
PG_USER = os.getenv("PG_USER", "postgres")
PG_PASSWORD = os.getenv("PG_PASSWORD", SUPABASE_DB_PASSWORD)
PG_HOST = os.getenv("PG_HOST", "")
PG_PORT = os.getenv("PG_PORT", "5432")
PG_DB = os.getenv("PG_DB", "postgres")

# Database mode: use DATABASE_URL if set, else Supabase config, else SQLite
if os.getenv("DATABASE_URL"):
    DATABASE_URL = os.getenv("DATABASE_URL")
    # Render uses postgres:// but SQLAlchemy needs postgresql+asyncpg://
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
    elif DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
elif PG_HOST:
    DATABASE_URL = f"postgresql+asyncpg://{PG_USER}:{quote_plus(PG_PASSWORD)}@{PG_HOST}:{PG_PORT}/{PG_DB}"
else:
    DATABASE_URL = f"sqlite+aiosqlite:///{BASE_DIR}/examguard.db"

# API Configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))

# CORS - comma-separated allowed origins (use * for dev)
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:4173,http://localhost:3000").split(",")

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

# ==================== URL CLASSIFICATION LISTS ====================

# AI / LLM sites - high risk
AI_SITES = [
    "chat.openai.com", "chatgpt.com", "openai.com",
    "gemini.google.com", "bard.google.com",
    "claude.ai", "anthropic.com",
    "perplexity.ai",
    "copilot.microsoft.com", "bing.com/chat",
    "poe.com", "character.ai",
    "huggingface.co/chat", "deepseek.com",
    "you.com", "phind.com",
    "wolframalpha.com", "symbolab.com",
    "photomath.com", "mathway.com",
]

# Entertainment / distraction sites - medium risk
ENTERTAINMENT_SITES = [
    "youtube.com", "netflix.com", "hulu.com",
    "disneyplus.com", "primevideo.com",
    "twitch.tv", "kick.com",
    "tiktok.com", "instagram.com", "facebook.com", "twitter.com", "x.com",
    "reddit.com", "tumblr.com", "pinterest.com",
    "snapchat.com", "discord.com",
    "spotify.com", "music.youtube.com", "soundcloud.com",
    "store.steampowered.com", "epicgames.com",
    "crunchyroll.com", "roblox.com",
]

# Academic cheating sites - critical risk
CHEATING_SITES = [
    "chegg.com", "coursehero.com", "studocu.com",
    "quizlet.com", "brainly.com", "bartleby.com",
    "numerade.com", "slader.com", "litanswers.org",
    "stackoverflow.com", "stackexchange.com",
    "pastebin.com", "github.com", "gitlab.com",
]

def classify_url(url: str) -> dict | None:
    """Classify a URL into a risk category. Returns dict with category/site/riskLevel or None."""
    if not url:
        return None
    url_lower = url.lower()
    try:
        from urllib.parse import urlparse
        hostname = urlparse(url_lower).hostname or ""
        hostname = hostname.replace("www.", "")
    except Exception:
        hostname = url_lower

    for site in AI_SITES:
        if site in hostname or site in url_lower:
            return {"category": "AI", "site": site, "risk_level": "high"}
    for site in CHEATING_SITES:
        if site in hostname or site in url_lower:
            return {"category": "CHEATING", "site": site, "risk_level": "critical"}
    for site in ENTERTAINMENT_SITES:
        if site in hostname or site in url_lower:
            return {"category": "ENTERTAINMENT", "site": site, "risk_level": "medium"}
    return None

# Risk score weights
RISK_WEIGHTS = {
    "TAB_SWITCH": 10,
    "WINDOW_BLUR": 5,
    "FORBIDDEN_SITE": 40,
    "FORBIDDEN_CONTENT": 40,
    "AI_USAGE": 45,
    "ENTERTAINMENT": 25,
    "CHEATING_SITE": 50,
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
