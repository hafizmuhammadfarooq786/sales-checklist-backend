"""
Configuration settings for the Sales Checklist API
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
    PROJECT_NAME: str = "Sales Checklist™ API"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = Field(default="development")
    DEBUG: bool = Field(default=False)

    # Security
    SECRET_KEY: str = Field(default="your-secret-key-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Clerk Authentication
    CLERK_PUBLISHABLE_KEY: str = Field(default="")
    CLERK_SECRET_KEY: str = Field(default="")
    CLERK_JWT_VERIFICATION_KEY: str = Field(default="")

    # Database
    DATABASE_URL: str = Field(
        default="postgresql://neondb_owner:npg_cnFle7kXxLd0@ep-lucky-breeze-a4i6m6jo-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
    )
    DB_ECHO: bool = Field(default=False)

    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/0")

    # AWS
    AWS_REGION: str = Field(default="us-east-1")
    AWS_ACCESS_KEY_ID: str = Field(default="")
    AWS_SECRET_ACCESS_KEY: str = Field(default="")
    AWS_S3_BUCKET_NAME: str = Field(default="sales-checklist")
    S3_BUCKET_AUDIO: str = Field(default="sales-checklist-audio")
    S3_BUCKET_REPORTS: str = Field(default="sales-checklist-reports")
    S3_BUCKET_BACKUPS: str = Field(default="sales-checklist-backups")

    # OpenAI
    OPENAI_API_KEY: str = Field(default="")
    OPENAI_MODEL_WHISPER: str = "whisper-1"
    OPENAI_MODEL_GPT: str = "gpt-4-turbo-preview"

    # ElevenLabs
    ELEVENLABS_API_KEY: str = Field(default="")
    ELEVENLABS_VOICE_ID: str = Field(default="")

    # Celery
    CELERY_BROKER_URL: str = Field(default="redis://localhost:6379/1")
    CELERY_RESULT_BACKEND: str = Field(default="redis://localhost:6379/2")

    # CORS
    ALLOWED_ORIGINS: List[str] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:3001",
            "https://*.vercel.app",
        ]
    )

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    # File Upload
    MAX_UPLOAD_SIZE: int = Field(default=524288000)  # 500MB

    # Sentry
    SENTRY_DSN: str = Field(default="")

    # Email (Amazon SES)
    SES_REGION: str = Field(default="us-east-1")
    SES_SENDER_EMAIL: str = Field(default="")

    # Salesforce
    SALESFORCE_CLIENT_ID: str = Field(default="")
    SALESFORCE_CLIENT_SECRET: str = Field(default="")
    SALESFORCE_REDIRECT_URI: str = Field(default="")


settings = Settings()
