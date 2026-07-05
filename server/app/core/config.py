from pathlib import Path
from typing import List, Dict, Optional, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, validator, AnyHttpUrl
from urllib.parse import quote_plus
import os

class Settings(BaseSettings):
    # Base paths
    PROJECT_NAME: str = "ExamGuard Pro"
    VERSION: str = "2.0.0"
    API_V1_STR: str = "/api/v1"
    API_V2_STR: str = "/api/v2"
    
    BASE_DIR: Path = Path(__file__).parent.parent.parent
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    SCREENSHOTS_DIR: Path = UPLOAD_DIR / "screenshots"
    WEBCAM_DIR: Path = UPLOAD_DIR / "webcam"
    REPORTS_DIR: Path = UPLOAD_DIR / "reports"

    # Database Configuration
    SUPABASE_URL: str = Field(default="", env="SUPABASE_URL")
    SUPABASE_KEY: str = Field(default="", env="SUPABASE_KEY")
    SUPABASE_DB_PASSWORD: str = Field(default="", env="SUPABASE_DB_PASSWORD")
    
    PG_USER: str = Field(default="postgres", env="PG_USER")
    PG_PASSWORD: str = Field(default="", env="PG_PASSWORD")
    PG_HOST: str = Field(default="", env="PG_HOST")
    PG_PORT: str = Field(default="5432", env="PG_PORT")
    PG_DB: str = Field(default="postgres", env="PG_DB")
    
    DATABASE_URL: Optional[str] = Field(default=None, env="DATABASE_URL")

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        if self.DATABASE_URL:
            url = self.DATABASE_URL
            if url.startswith("postgres://"):
                return url.replace("postgres://", "postgresql+asyncpg://", 1)
            elif url.startswith("postgresql://"):
                return url.replace("postgresql://", "postgresql+asyncpg://", 1)
            return url
        
        if self.PG_HOST:
            password = self.PG_PASSWORD or self.SUPABASE_DB_PASSWORD
            return f"postgresql+asyncpg://{self.PG_USER}:{quote_plus(password)}@{self.PG_HOST}:{self.PG_PORT}/{self.PG_DB}"
        
        return f"sqlite+aiosqlite:///{self.BASE_DIR}/examguard.db"

    # Security
    SECRET_KEY: str = Field(default="secret-key-keep-it-safe", env="SECRET_KEY")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    CORS_ORIGINS: Union[str, List[str]] = "*"

    # AI / ML Settings
    ENABLE_OBJECT_DETECTION: bool = True
    MIN_FACE_CONFIDENCE: float = 0.7
    FACE_ABSENCE_THRESHOLD_SECONDS: int = 10
    OCR_LANGUAGE: str = "eng"
    TEXT_SIMILARITY_THRESHOLD: float = 0.75
    
    # Capture Settings
    SCREENSHOT_INTERVAL_SECONDS: int = 3
    WEBCAM_INTERVAL_SECONDS: int = 5
    IMAGE_QUALITY: float = 0.7

    # Risk Weights
    RISK_WEIGHTS: Dict[str, float] = {
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
        "CLICK": 1,
        "TYPING": 1,
        "VISIBILITY_CHANGE": 5,
        "BROWSER_FOCUS_LOST": 5,
        "WINDOW_RESIZE": 5,
        "VISUAL_FORBIDDEN_CONTENT": 45,
    }

    # Forbidden lists
    AI_SITES: List[str] = [
        "chat.openai.com", "chatgpt.com", "openai.com",
        "gemini.google.com", "bard.google.com",
        "claude.ai", "anthropic.com",
        "perplexity.ai", "poe.com", "character.ai",
        "huggingface.co/chat", "deepseek.com",
        "you.com", "phind.com", "wolframalpha.com",
    ]
    
    CHEATING_SITES: List[str] = [
        "chegg.com", "coursehero.com", "studocu.com",
        "quizlet.com", "brainly.com", "bartleby.com",
        "numerade.com", "slader.com", "litanswers.org",
        "stackoverflow.com", "stackexchange.com",
    ]

    # Tools
    FFMPEG_PATH: Optional[str] = Field(default=None, env="FFMPEG_PATH")

    # Redis / Celery
    REDIS_URL: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    CELERY_BROKER_URL: str = Field(default="redis://localhost:6379/0", env="CELERY_BROKER_URL")
    CELERY_RESULT_BACKEND: str = Field(default="redis://localhost:6379/0", env="CELERY_RESULT_BACKEND")
    EVENTS_RATE_LIMIT_PER_SECOND: int = Field(default=10, env="EVENTS_RATE_LIMIT_PER_SECOND")

    # Storage
    REPORTS_BUCKET: str = Field(default="reports", env="REPORTS_BUCKET")
    SCREENSHOTS_BUCKET: str = Field(default="screenshots", env="SCREENSHOTS_BUCKET")

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

    @property
    def cors_origins_list(self) -> List[str]:
        if self.CORS_ORIGINS == "*":
            return ["*"]
        if isinstance(self.CORS_ORIGINS, str):
            return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]
        return list(self.CORS_ORIGINS)

settings = Settings()
