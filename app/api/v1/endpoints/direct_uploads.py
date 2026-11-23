"""
Direct upload to S3 for manager voice notes and knowledge base documents.

Staging runs on AWS Lambda, where a request cannot carry more than 6 MB. A
voice note can be 10 MB and a knowledge document 20 MB. With
DIRECT_UPLOADS_ENABLED the browser asks for a signed form, sends the file
straight to S3, then tells the API it is there. Session audio does the same
in uploads.py, and the reasoning is written out there.

With the setting off, which is the default and what production uses, every
route here answers 404 and the existing uploads are the only path. Nothing in
manager_notes.py or knowledge_base.py is changed by this file: it reuses their
permission checks and makes the same records they make.
"""
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies import get_current_user, require_roles
from app.api.v1.endpoints.knowledge_base import (
    _enqueue_document_processing,
    _require_org_id,
)
from app.api.v1.endpoints.manager_notes import (
    _schedule_rep_manager_note_notification,
    _user_display_name,
    can_add_note,
    can_view_session,
    get_audio_url,
)
from app.api.v1.endpoints.uploads import (
    DIRECT_UPLOAD_EXPIRES_SECONDS,
    DirectUploadRequest,
    key_is_directly_under,
    require_direct_uploads,
)
from app.core.config import settings
from app.db.session import get_db
from app.models import User
from app.models.manager_note import ManagerNote, NoteType
from app.models.organization_knowledge import OrganizationKnowledgeDocument
from app.models.session import Session
from app.models.user import UserRole
from app.schemas.knowledge_base import (
    KnowledgeDocumentResponse,
    KnowledgeDocumentUploadResponse,
)
from app.schemas.manager_note import ManagerNoteResponse
from app.services.knowledge_ingestion_service import record_uploaded_knowledge_file
from app.services.knowledge_text_extractor import (
    is_allowed_knowledge_content_type,
    normalize_content_type,
)
from app.services.s3_service import get_s3_service

logger = logging.getLogger(__name__)

notes_router = APIRouter()
knowledge_router = APIRouter()

VOICE_NOTE_MAX_BYTES = 10 * 1024 * 1024  # same limit as POST /notes/audio

# One object, so a test can stand in for it.
require_admin = require_roles(UserRole.ADMIN)


def _signed_form(key: str, form: dict) -> dict:
    return {
        "url": form["url"],
        "fields": form["fields"],
        "key": key,
        "expires_in": DIRECT_UPLOAD_EXPIRES_SECONDS,
    }


# ---------------------------------------------------------------------------
# Manager voice notes
# ---------------------------------------------------------------------------


class VoiceNoteUploadComplete(BaseModel):
    key: str
    duration: Optional[int] = None


def voice_note_key_prefix(user_id: int, session_id: int) -> str:
    return f"manager_notes/{user_id}/{session_id}/"


def _require_can_add_note(user: User) -> None:
    if not can_add_note(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only managers and admins can add coaching notes",
        )


async def _session_for_note(db: AsyncSession, session_id: int, user: User) -> Session:
    result = await db.execute(
        select(Session).where(Session.id == session_id).options(selectinload(Session.user))
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if not can_view_session(user, session):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to add notes to this session",
        )
    return session


def _note_response(note: ManagerNote, manager: User) -> ManagerNoteResponse:
    response = ManagerNoteResponse.model_validate(note)
    response.manager_name = _user_display_name(manager)
    response.audio_url = get_audio_url(note)
    return response


@notes_router.post("/{session_id}/notes/audio/upload-url")
async def create_voice_note_upload_url(
    session_id: int,
    body: DirectUploadRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Step 1: a signed form for one voice note."""
    require_direct_uploads()
    _require_can_add_note(current_user)

    if not body.content_type or not body.content_type.startswith("audio/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Expected audio file, got {body.content_type}",
        )
    if body.file_size <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")
    if body.file_size > VOICE_NOTE_MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size is 10MB, got {body.file_size / 1024 / 1024:.2f}MB",
        )

    await _session_for_note(db, session_id, current_user)

    extension = body.filename.rsplit(".", 1)[-1] if "." in (body.filename or "") else "webm"
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    # The random part keeps two notes recorded in the same second apart.
    name = f"note_{current_user.id}_{session_id}_{timestamp}_{uuid.uuid4().hex[:8]}.{extension}"
    key = voice_note_key_prefix(current_user.id, session_id) + name
    form = await run_in_threadpool(
        get_s3_service().generate_presigned_upload,
        key,
        body.content_type,
        VOICE_NOTE_MAX_BYTES,
        DIRECT_UPLOAD_EXPIRES_SECONDS,
    )
    return _signed_form(key, form)


@notes_router.post(
    "/{session_id}/notes/audio/upload-complete",
    response_model=ManagerNoteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def complete_voice_note_upload(
    session_id: int,
    body: VoiceNoteUploadComplete,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Step 2: record the note and tell the rep, as POST /notes/audio does."""
    require_direct_uploads()
    _require_can_add_note(current_user)

    if not key_is_directly_under(body.key, voice_note_key_prefix(current_user.id, session_id)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "INVALID_UPLOAD_KEY"},
        )

    session = await _session_for_note(db, session_id, current_user)

    # Called twice (a retry, a double click): answer as the first call did.
    # No second note, no second email to the rep.
    existing_result = await db.execute(
        select(ManagerNote).where(ManagerNote.audio_s3_key == body.key)
    )
    existing = existing_result.scalars().first()
    if existing:
        return _note_response(existing, current_user)

    info = await run_in_threadpool(get_s3_service().object_info, body.key)
    if not info:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "UPLOAD_NOT_FOUND", "message": "The file has not arrived in storage."},
        )
    if info["size"] > VOICE_NOTE_MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size is 10MB, got {info['size'] / 1024 / 1024:.2f}MB",
        )

    note = ManagerNote(
        session_id=session_id,
        manager_id=current_user.id,
        note_type=NoteType.AUDIO,
        note_text=None,
        is_edited=False,
        audio_s3_bucket=settings.s3_audio_bucket,
        audio_s3_key=body.key,
        audio_file_size=info["size"],
        audio_duration=body.duration,
    )
    db.add(note)
    await db.commit()
    await db.refresh(note)
    logger.info(
        "Manager %s added audio note to session %s (direct upload)", current_user.id, session_id
    )

    await _schedule_rep_manager_note_notification(
        background_tasks,
        session=session,
        manager=current_user,
        note_type=NoteType.AUDIO,
    )
    return _note_response(note, current_user)


# ---------------------------------------------------------------------------
# Knowledge base documents
# ---------------------------------------------------------------------------


class KnowledgeUploadComplete(BaseModel):
    key: str
    filename: str


def knowledge_key_prefix(organization_id: int) -> str:
    return f"knowledge-base/{organization_id}/"


@knowledge_router.post("/documents/upload-url")
async def create_knowledge_upload_url(
    body: DirectUploadRequest,
    current_user: User = Depends(require_admin),
):
    """Step 1: a signed form for one knowledge document."""
    require_direct_uploads()
    organization_id = _require_org_id(current_user)

    content_type = normalize_content_type(body.content_type or "")
    if not is_allowed_knowledge_content_type(content_type):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Supported types: PDF, DOCX, TXT, and Markdown",
        )
    if body.file_size <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")
    if body.file_size > settings.KNOWLEDGE_BASE_MAX_FILE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File exceeds maximum allowed size",
        )

    extension = Path(body.filename or "document").suffix or ".bin"
    key = f"{knowledge_key_prefix(organization_id)}{uuid.uuid4().hex}{extension}"
    form = await run_in_threadpool(
        get_s3_service().generate_presigned_upload,
        key,
        content_type,
        settings.KNOWLEDGE_BASE_MAX_FILE_BYTES,
        DIRECT_UPLOAD_EXPIRES_SECONDS,
    )
    return _signed_form(key, form)


@knowledge_router.post(
    "/documents/upload-complete",
    response_model=KnowledgeDocumentUploadResponse,
)
async def complete_knowledge_upload(
    body: KnowledgeUploadComplete,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Step 2: record the document and start indexing, as POST /documents does."""
    require_direct_uploads()
    organization_id = _require_org_id(current_user)

    if not key_is_directly_under(body.key, knowledge_key_prefix(organization_id)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "INVALID_UPLOAD_KEY"},
        )

    # Called twice: answer with the document already recorded, index once.
    existing_result = await db.execute(
        select(OrganizationKnowledgeDocument).where(
            OrganizationKnowledgeDocument.organization_id == organization_id,
            OrganizationKnowledgeDocument.s3_key == body.key,
        )
    )
    existing = existing_result.scalars().first()
    if existing:
        return KnowledgeDocumentUploadResponse(
            document=KnowledgeDocumentResponse.model_validate(existing),
            message="Document uploaded. Indexing has started.",
        )

    info = await run_in_threadpool(get_s3_service().object_info, body.key)
    if not info:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "UPLOAD_NOT_FOUND", "message": "The file has not arrived in storage."},
        )
    if info["size"] > settings.KNOWLEDGE_BASE_MAX_FILE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File exceeds maximum allowed size",
        )
    content_type = normalize_content_type(info.get("content_type") or "")
    if not is_allowed_knowledge_content_type(content_type):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Supported types: PDF, DOCX, TXT, and Markdown",
        )

    document = await record_uploaded_knowledge_file(
        organization_id=organization_id,
        uploaded_by_user_id=current_user.id,
        original_filename=body.filename or "document",
        content_type=content_type,
        file_size_bytes=info["size"],
        s3_key=body.key,
    )
    _enqueue_document_processing(background_tasks, document.id)

    return KnowledgeDocumentUploadResponse(
        document=KnowledgeDocumentResponse.model_validate(document),
        message="Document uploaded. Indexing has started.",
    )
