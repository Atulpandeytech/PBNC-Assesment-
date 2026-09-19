import os
from typing import List, Optional, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Application
    APP_NAME: str = "PragatiBhartiDocumentIntelligence"
    APP_ENV: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    CORS_ORIGINS: Union[List[str], str] = ["*"]

    # Security & JWT
    SECRET_KEY: str = "change-this-to-a-super-secret-key-in-production-min-32-chars"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/pragati_bharti.db"

    # Redis & Rate Limit
    REDIS_URL: str = "redis://localhost:6379/0"
    RATE_LIMIT_ENABLED: bool = False
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 120

    # Storage
    STORAGE_BACKEND: str = "local"  # "local" or "s3"
    STORAGE_LOCAL_ROOT: str = "./data/storage"
    MAX_UPLOAD_SIZE_BYTES: int = 52428800  # 50 MB
    MAX_PAGE_COUNT: int = 100

    # S3 / MinIO (optional)
    S3_ENDPOINT_URL: Optional[str] = None
    S3_ACCESS_KEY: Optional[str] = None
    S3_SECRET_KEY: Optional[str] = None
    S3_BUCKET_NAME: str = "pragati-bharti-documents"
    S3_REGION: str = "us-east-1"

    # OCR & AI
    TESSERACT_CMD: Optional[str] = None
    LLM_ENABLED: bool = False
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.5-flash"
    LLM_TIMEOUT_SECONDS: int = 30
    LLM_MAX_RETRIES: int = 3

    # Confidence Thresholds
    CONFIDENCE_THRESHOLD_HIGH: float = 0.85
    CONFIDENCE_THRESHOLD_LOW: float = 0.60
    WORKER_CONCURRENCY: int = 4

    @field_validator("CORS_ORIGINS", mode="before")
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [x.strip() for x in v.split(",") if x.strip()]
        return v


settings = Settings()
