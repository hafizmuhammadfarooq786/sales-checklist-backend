"""In-app help — fallback answering for questions the approved corpus misses.

Requires only an authenticated user: this endpoint reads no opportunity data and
no organization knowledge, so it carries none of the per-deal access checks that
the session knowledge endpoints do.
"""
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.api.dependencies import get_current_active_user
from app.models.user import User
from app.services.app_help_service import stream_app_help_answer

router = APIRouter()


class AppHelpContextEntry(BaseModel):
    question: str
    answer: str
    source: str = ""


class AppHelpAskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    # The approved entries the client considered — the only material the model
    # may answer from.
    context: list[AppHelpContextEntry] = Field(default_factory=list, max_length=12)
    screen: str | None = None


@router.post("/ask")
async def ask_app_help(
    payload: AppHelpAskRequest,
    current_user: User = Depends(get_current_active_user),
):
    """Stream a grounded answer back as plain text chunks."""
    generator = stream_app_help_answer(
        question=payload.question,
        context_entries=[entry.model_dump() for entry in payload.context],
        screen=payload.screen,
        role=getattr(current_user.role, "value", current_user.role),
    )
    return StreamingResponse(
        generator,
        media_type="text/plain; charset=utf-8",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )
