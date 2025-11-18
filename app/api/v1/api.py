"""
API v1 router
"""
from fastapi import APIRouter

from app.api.v1.endpoints import checklists, sessions, users, uploads, responses

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(checklists.router, prefix="/checklists", tags=["Checklists"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["Sessions"])
api_router.include_router(responses.router, prefix="/sessions", tags=["Responses"])
api_router.include_router(uploads.router, prefix="/sessions", tags=["Uploads"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])


@api_router.get("/")
async def api_root():
    """API v1 root endpoint"""
    return {
        "message": "Sales Checklist™ API v1",
        "status": "active",
        "version": "1.0.0",
        "endpoints": {
            "checklists": "/checklists",
            "sessions": "/sessions",
            "users": "/users",
            "docs": "/docs",
            "health": "/health"
        }
    }
