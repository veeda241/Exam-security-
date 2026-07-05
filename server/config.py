"""Application settings (Pydantic)."""
from pathlib import Path
from typing import Dict, List, Optional, Union
from urllib.parse import quote_plus

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "ExamGuard Pro"
    VERSION: str = "2.0.0"
    API_V1_STR: str = "/api/v1"

    BASE_DIR: Path = Path(__file__).parent
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    SCREENSHOTS_DIR: Path = UPLOAD_DIR / "screenshots"
    WEBCAM_DIR: Path = UPLOAD_DIR / "webcam"
    REPORTS_DIR: Path = UPLOAD_DIR / "reports"

    SUPABASE_URL: str = Field(default="", env="SUPABASE_URL")
    SUPABASE_KEY: str = Field(default="", env="SUPABASE_KEY")
    SUPABASE_DB_PASSWORD: str = Field(default="", env="SUPABASE_DB_PASSWORD")

    PG_USER: str = Field(default="postgres", env="PG_USER")
    PG_PASSWORD: str = Field(default="", env="PG_PASSWORD")
    PG_HOST: str = Field(default="", env="PG_HOST")
    PG_PORT: str = Field(default="5432", env="PG_PORT")
    PG_DB: str = Field(default="postgres", env="PG_DB")
    DATABASE_URL: Optional[str] = Field(default=None, env="DATABASE_URL")

    SECRET_KEY: str = Field(default="secret-key-keep-it-safe", env="SECRET_KEY")
    CORS_ORIGINS: Union[str, List[str]] = "*"

    ENABLE_OBJECT_DETECTION: bool = True
    OCR_LANGUAGE: str = "eng"
    WEBCAM_INTERVAL_SECONDS: int = 5

    REDIS_URL: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    CELERY_BROKER_URL: str = Field(default="redis://localhost:6379/0", env="CELERY_BROKER_URL")
    CELERY_RESULT_BACKEND: str = Field(default="redis://localhost:6379/0", env="CELERY_RESULT_BACKEND")
    EVENTS_RATE_LIMIT_PER_SECOND: int = Field(default=10, env="EVENTS_RATE_LIMIT_PER_SECOND")

    REPORTS_BUCKET: str = Field(default="reports", env="REPORTS_BUCKET")
    SCREENSHOTS_BUCKET: str = Field(default="screenshots", env="SCREENSHOTS_BUCKET")

    RISK_WEIGHTS: Dict[str, float] = {
        "tab_switch": 10,
        "window_blur": 5,
        "copy_paste": 15,
        "face_missing": 20,
        "multiple_faces": 25,
        "gaze_away": 15,
        "ocr_flag": 40,
        "object_flag": 25,
        "text_similarity": 35,
        "forbidden_site": 40,
        "page_hidden": 8,
        "TAB_SWITCH": 10,
        "WINDOW_BLUR": 5,
        "FORBIDDEN_CONTENT": 40,
        "FACE_ABSENT": 20,
        "COPY": 15,
        "PASTE": 10,
    }

    RISK_THRESHOLDS: Dict[str, float] = {"review": 30, "suspicious": 60}

    FORBIDDEN_KEYWORDS: List[str] = [
        "chatgpt", "chegg", "stackoverflow", "quizlet", "brainly",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        if self.DATABASE_URL:
            url = self.DATABASE_URL
            if url.startswith("postgres://"):
                return url.replace("postgres://", "postgresql+asyncpg://", 1)
            if url.startswith("postgresql://"):
                return url.replace("postgresql://", "postgresql+asyncpg://", 1)
            return url
        if self.PG_HOST:
            password = self.PG_PASSWORD or self.SUPABASE_DB_PASSWORD
            return f"postgresql+asyncpg://{self.PG_USER}:{quote_plus(password)}@{self.PG_HOST}:{self.PG_PORT}/{self.PG_DB}"
        return f"sqlite+aiosqlite:///{self.BASE_DIR}/examguard.db"

    @property
    def cors_origins_list(self) -> List[str]:
        if self.CORS_ORIGINS == "*":
            return ["*"]
        if isinstance(self.CORS_ORIGINS, str):
            return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]
        return list(self.CORS_ORIGINS)


settings = Settings()

# Legacy V1 service compatibility
SUPABASE_URL = settings.SUPABASE_URL
SUPABASE_KEY = settings.SUPABASE_KEY
SUPABASE_DB_PASSWORD = settings.SUPABASE_DB_PASSWORD
DATABASE_URL = settings.ASYNC_DATABASE_URL
RISK_WEIGHTS = settings.RISK_WEIGHTS
RISK_THRESHOLDS = settings.RISK_THRESHOLDS
FORBIDDEN_KEYWORDS = settings.FORBIDDEN_KEYWORDS
OCR_LANGUAGE = settings.OCR_LANGUAGE
ENABLE_OBJECT_DETECTION = settings.ENABLE_OBJECT_DETECTION
WEBCAM_INTERVAL_SECONDS = settings.WEBCAM_INTERVAL_SECONDS
SCREENSHOTS_DIR = settings.SCREENSHOTS_DIR
WEBCAM_DIR = settings.WEBCAM_DIR
UPLOAD_DIR = settings.UPLOAD_DIR
REPORTS_DIR = settings.REPORTS_DIR
API_HOST = "0.0.0.0"
API_PORT = 8000

AI_SITES = settings.AI_SITES if hasattr(settings, "AI_SITES") else []
CHEATING_SITES = settings.CHEATING_SITES if hasattr(settings, "CHEATING_SITES") else []
ENTERTAINMENT_SITES = []
SOCIAL_SITES = []
EDUCATIONAL_SITES = []


def classify_url(url: str, title: str = "") -> dict | None:
    """Legacy URL classifier shim for V1 services."""
    try:
        from services.page_classifier import classify_page
        result = classify_page(url=url, title=title)
        if result.tracker_category == "other" and result.confidence < 0.35:
            return None
        return {
            "category": result.category,
            "site": (title or url)[:80],
            "risk_level": result.risk_level,
        }
    except Exception:
        return None
