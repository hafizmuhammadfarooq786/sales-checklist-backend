"""
Sales Checklist™ API - Main Application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.api.v1.api import api_router
from app.db.session import engine
from app.models import Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for startup and shutdown."""
    # Startup
    print("🚀 Starting Sales Checklist API...")
    async with engine.begin() as conn:
        # Create tables if they don't exist (dev only)
        if settings.ENVIRONMENT == "development":
            await conn.run_sync(Base.metadata.create_all)

    yield

    # Shutdown
    print("🛑 Shutting down Sales Checklist API...")
    await engine.dispose()


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
