"""Application configuration and environment settings for MAPORA backend."""

from typing import List, Optional, Union
import os
from pathlib import Path
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Central configuration for MAPORA backend services."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # General
    APP_NAME: str = "MAPORA Backend"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    PORT: int = 8000
    HOST: str = "0.0.0.0"

    # Security & JWT
    SECRET_KEY: str = Field(
        default="mapora_super_secret_jwt_key_change_in_production_9f8e7d6c5b4a3",
        description="Cryptographic secret key for signing JWTs",
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Rate Limiting
    RATE_LIMIT_AUTH: str = "10/minute"
    RATE_LIMIT_UPLOAD: str = "5/minute"

    # CORS
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v):
        if isinstance(v, str):
            if v.strip().startswith("["):
                import json
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return []

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/mapora",
        description="PostgreSQL connection string. Fallback to SQLite if configured or for tests.",
    )
    SQL_ECHO: bool = False

    # Redis & Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: Optional[str] = None
    CELERY_RESULT_BACKEND: Optional[str] = None

    # Storage: "local" or "s3"
    STORAGE_BACKEND: str = "local"
    LOCAL_STORAGE_DIR: str = str(BASE_DIR / "storage_data")

    # S3 / MinIO Settings
    S3_ENDPOINT_URL: Optional[str] = None
    S3_ACCESS_KEY_ID: Optional[str] = None
    S3_SECRET_ACCESS_KEY: Optional[str] = None
    S3_BUCKET_NAME: str = "mapora-uploads"
    S3_REGION_NAME: str = "us-east-1"
    S3_SECURE: bool = False

    # Video Upload Constraints
    MAX_UPLOAD_SIZE_BYTES: int = 500 * 1024 * 1024  # 500 MB
    ALLOWED_VIDEO_EXTENSIONS: List[str] = [".mp4", ".mov", ".m4v", ".avi"]
    ALLOWED_VIDEO_MIME_TYPES: List[str] = [
        "video/mp4",
        "video/quicktime",
        "video/x-m4v",
        "video/x-msvideo",
    ]

    # Computer Vision & Reconstruction Settings
    MODEL_WEIGHTS_DIR: str = str(BASE_DIR / "models_cache")
    DEVICE: str = "cpu"  # "cuda" if GPU is available
    KEYFRAME_MIN_INTERVAL_SECONDS: float = 0.5
    KEYFRAME_BLUR_THRESHOLD: float = 100.0  # Laplacian variance threshold
    KEYFRAME_FEATURE_DIFF_RATIO: float = 0.25
    MIDAS_MODEL_TYPE: str = "MiDaS_small"  # MiDaS_small, DPT_Hybrid, DPT_Large

    # Admin User Seed (Optional initial admin)
    INITIAL_ADMIN_EMAIL: Optional[str] = "admin@mapora.io"
    INITIAL_ADMIN_PASSWORD: Optional[str] = "AdminMapora2026!"


settings = Settings()

# Ensure directories exist
os.makedirs(settings.LOCAL_STORAGE_DIR, exist_ok=True)
os.makedirs(settings.MODEL_WEIGHTS_DIR, exist_ok=True)
