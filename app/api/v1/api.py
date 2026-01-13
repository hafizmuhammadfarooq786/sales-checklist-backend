"""
API v1 router
"""
from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    checklists,
    sessions,
    users,
    uploads,
    scoring,
    transcription,
    coaching,
    reports,
    admin,
    organization,
)
from app.api.v1.endpoints import responses_simple as responses

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router)
api_router.include_router(checklists.router, prefix="/checklists", tags=["Checklists"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["Sessions"])
api_router.include_router(responses.router, prefix="/sessions", tags=["Responses"])
api_router.include_router(uploads.router, prefix="/sessions", tags=["Uploads"])
api_router.include_router(scoring.router, prefix="/sessions", tags=["Scoring"])
api_router.include_router(transcription.router, prefix="/sessions", tags=["Transcription"])
api_router.include_router(coaching.router, prefix="/sessions", tags=["Coaching"])
api_router.include_router(reports.router, prefix="/sessions", tags=["Reports"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(admin.router, prefix="/admin", tags=["Admin - SYSTEM_ADMIN"])
api_router.include_router(organization.router, prefix="/organization", tags=["Organization Management"])


@api_router.get("/")
async def api_root():
    """API v1 root endpoint"""
    return {
        "message": "The Sales Checklist™ API v1",
        "status": "active",
        "version": "1.0.0",
        "endpoints": {
            "auth": "/auth",
            "checklists": "/checklists",
            "sessions": "/sessions",
            "users": "/users",
            "admin": "/admin (SYSTEM_ADMIN only)",
            "organization": "/organization (ADMIN/MANAGER)",
            "docs": "/docs",
            "health": "/health"
        }
    }
