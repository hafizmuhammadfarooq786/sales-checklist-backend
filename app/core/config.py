"""
Configuration settings for The Sales Checklist™ API
"""
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # App
    PROJECT_NAME: str = "The Sales Checklist™ API"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = Field(default="development")
    DEBUG: bool = Field(default=False)

    # Security & JWT Authentication
    SECRET_KEY: str = Field(default="", description="JWT signing secret - MUST be set via environment variable")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # Default fallback (7 days)
    SESSION_TOKEN_EXPIRE_MINUTES: int = 60 * 8  # Standard login without remember-me
    REMEMBER_ME_TOKEN_EXPIRE_DAYS: int = 30
    ALLOW_PUBLIC_SIGNUP: bool = Field(default=False)
    INTERNAL_ADMIN_API_KEY: str = Field(default="")
    
    # Password validation
    MIN_PASSWORD_LENGTH: int = 8
    REQUIRE_PASSWORD_UPPERCASE: bool = True
    REQUIRE_PASSWORD_LOWERCASE: bool = True
    REQUIRE_PASSWORD_NUMBERS: bool = True
    REQUIRE_PASSWORD_SPECIAL: bool = False

    # Database
    DATABASE_URL: str = Field(
        default="",
        description="Database connection URL - MUST be set via environment variable"
    )
    DB_ECHO: bool = Field(default=False)

    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/0")

    # AWS
    AWS_REGION: str = Field(default="us-east-2")
    AWS_ACCESS_KEY_ID: str = Field(default="")
    AWS_SECRET_ACCESS_KEY: str = Field(default="")
    AWS_S3_BUCKET_NAME: str = Field(default="")
    S3_BUCKET_AUDIO: str = Field(default="sales-checklist-audio")
    S3_BUCKET_REPORTS: str = Field(default="sales-checklist-reports")

    @property
    def s3_audio_bucket(self) -> str:
        """Primary bucket for session audio uploads (ECS: set S3_BUCKET_AUDIO)."""
        return self.AWS_S3_BUCKET_NAME or self.S3_BUCKET_AUDIO

    # OpenAI
    OPENAI_API_KEY: str = Field(default="")
    OPENAI_MODEL_WHISPER: str = "whisper-1"
    OPENAI_MODEL_GPT: str = "gpt-4o"

    # Celery
    CELERY_BROKER_URL: str = Field(default="redis://localhost:6379/1")
    CELERY_RESULT_BACKEND: str = Field(default="redis://localhost:6379/2")
    # When True, transcription runs in a Celery worker (requires Redis + worker process).
    # When False or broker unavailable, upload/transcribe endpoints fall back to BackgroundTasks.
    USE_CELERY_FOR_TRANSCRIPTION: bool = Field(default=False)

    # CORS
    ALLOWED_ORIGINS: List[str] = Field(
        default=["http://localhost:3000"]
    )

    # Frontend URL (for invitation emails and redirects)
    # Set in .env to your deployed UI so invitation "Accept" links point to your app (e.g. https://app.yourdomain.com)
    FRONTEND_URL: str = Field(default="http://localhost:3000")

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    # File Upload
    MAX_UPLOAD_SIZE: int = Field(default=524288000)  # 500MB

    # Audio Upload Settings (aligned with OpenAI Whisper limits)
    MAX_AUDIO_FILE_SIZE_MB: int = Field(default=25, description="Maximum audio file size in MB (OpenAI Whisper limit)")
    AUDIO_CHUNK_SIZE_MB: int = Field(default=5, description="Chunk size for resumable uploads")
    AUDIO_UPLOAD_TIMEOUT_SECONDS: int = Field(default=300, description="Upload timeout in seconds (5 minutes)")

    # Audio Compression Recommendations (for frontend documentation)
    RECOMMENDED_AUDIO_BITRATE: str = "64k"
    RECOMMENDED_AUDIO_SAMPLE_RATE: int = 22050

    # Sentry
    SENTRY_DSN: str = Field(default="")

    # Email (Amazon SES)
    SES_REGION: str = Field(default="us-east-2")
    SES_SENDER_EMAIL: str = Field(default="")

    # Email transport: auto (from ENVIRONMENT), smtp (local dev), or ses (stage/prod).
    # Local/development → SMTP only. Staging/production → SES only (no SMTP fallback).
    EMAIL_PROVIDER: str = Field(default="auto")
    EMAIL_COMPANY_NAME: str = Field(default="The Millau Group Global")

    # Email (SMTP — local development)
    SMTP_HOST: str = Field(default="")
    SMTP_PORT: int = Field(default=587)
    SMTP_USERNAME: str = Field(default="")
    SMTP_PASSWORD: str = Field(default="")
    SMTP_SENDER_EMAIL: str = Field(default="")
    SMTP_USE_TLS: bool = Field(default=True)
    SMTP_USE_SSL: bool = Field(default=False)
    SMTP_TIMEOUT_SECONDS: int = Field(default=30)

    @property
    def email_provider(self) -> str:
        """Resolve email transport: smtp for local dev, ses for stage/prod."""
        explicit = (self.EMAIL_PROVIDER or "auto").strip().lower()
        if explicit in ("smtp", "ses"):
            return explicit
        env = (self.ENVIRONMENT or "development").strip().lower()
        if env in ("production", "prod", "staging", "stage"):
            return "ses"
        return "smtp"


settings = Settings()
