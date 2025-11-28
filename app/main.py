"""
Sales Checklist™ API - Main Application
"""
import logging
from logging.handlers import RotatingFileHandler
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.api.v1.api import api_router
from app.db.session import engine
from app.models import Base


# Configure logging
def setup_logging():
    """Setup application logging with file and console handlers"""
    # Create logs directory if it doesn't exist
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Configure log format
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    # Set log level based on environment
    log_level = logging.DEBUG if settings.ENVIRONMENT == "development" else logging.INFO

    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[
            # File handler with rotation (10MB per file, keep 10 backups)
            RotatingFileHandler(
                os.path.join(log_dir, 'app.log'),
                maxBytes=10485760,  # 10MB
                backupCount=10,
                encoding='utf-8'
            ),
            # Console handler
            logging.StreamHandler()
        ]
    )

    # Set specific log levels for noisy libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('boto3').setLevel(logging.WARNING)
    logging.getLogger('botocore').setLevel(logging.WARNING)
    logging.getLogger('s3transfer').setLevel(logging.WARNING)


# Initialize logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for startup and shutdown."""
    # Startup
    logger.info("🚀 Starting Sales Checklist API...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"API Version: {settings.API_V1_STR}")

    async with engine.begin() as conn:
        # Create tables if they don't exist (dev only)
        if settings.ENVIRONMENT == "development":
            logger.info("Development mode: Creating database tables if they don't exist")
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables initialized")

    logger.info("API startup complete")
    yield

    # Shutdown
    logger.info("🛑 Shutting down Sales Checklist API...")
    await engine.dispose()
    logger.info("Database connections closed")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="AI-Powered B2B Sales Coaching Platform API",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GZip compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# API router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "sales-checklist-api",
        "version": "1.0.0"
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Sales Checklist™ API",
        "docs": f"{settings.API_V1_STR}/docs",
        "health": "/health"
    }
