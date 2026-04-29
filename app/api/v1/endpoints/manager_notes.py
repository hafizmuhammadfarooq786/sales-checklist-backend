"""
Manager Notes API endpoints - Coaching feedback system
"""
import logging
import os
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import Optional

from app.db.session import get_db
from app.models.manager_note import ManagerNote, NoteType
from app.models.session import Session
from app.models.user import User, UserRole
from app.schemas.manager_note import (
    ManagerNoteCreate,
    ManagerNoteUpdate,
    ManagerNoteResponse,
    ManagerNoteListResponse
)
from app.api.dependencies import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)


def get_audio_url(note: ManagerNote) -> Optional[str]:
    """
    Generate a presigned URL or accessible URL for audio note.

    Args:
        note: ManagerNote instance with audio

    Returns:
        URL string if audio exists, None otherwise
    """
    if not note.audio_s3_key or note.note_type != NoteType.AUDIO:
        return None

    from app.services.s3_service import get_s3_service

    # If audio is stored in S3, generate presigned URL
    if note.audio_s3_bucket:
        try:
            s3_service = get_s3_service()
            presigned_url = s3_service.generate_presigned_url(
                note.audio_s3_key,
                expiration=3600,  # 1 hour
                bucket_name=note.audio_s3_bucket
            )
            if presigned_url:
                logger.info(f"Generated presigned URL for audio note {note.id}")
                return presigned_url
        except Exception as e:
            logger.error(f"Failed to generate presigned URL for audio note {note.id}: {e}")
            return None

    # For local storage, construct full URL (development fallback)
    logger.warning(f"Audio note {note.id} using local storage (development mode)")
    return None  # Local storage not supported for manager notes


def can_view_session(user: User, session: Session) -> bool:
    """
    Check if user can view this session (and thus add/view notes)

    RBAC Rules:
    - REP: Can only view own sessions
    - MANAGER: Can view sessions from their team
    - ADMIN: Can view all sessions in their organization
    - SYSTEM_ADMIN: Can view all sessions
    """
    if user.role == UserRole.SYSTEM_ADMIN:
        return True

    if user.role == UserRole.ADMIN:
        return session.user.organization_id == user.organization_id

    if user.role == UserRole.MANAGER:
        return session.user.team_id == user.team_id

    if user.role == UserRole.REP:
        return session.user_id == user.id

    return False


def can_add_note(user: User) -> bool:
    """
    Check if user can add notes (Manager or Admin only)
    """
    return user.role in [UserRole.MANAGER, UserRole.ADMIN, UserRole.SYSTEM_ADMIN]


@router.post("/{session_id}/notes", response_model=ManagerNoteResponse, status_code=status.HTTP_201_CREATED)
async def create_manager_note(
    session_id: int,
    note_data: ManagerNoteCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new manager note on a session

    **Permissions:**
    - MANAGER: Can add notes to sessions in their team
    - ADMIN: Can add notes to any session in their organization
    - SYSTEM_ADMIN: Can add notes to any session
    - REP: Cannot add notes
    """
    # Check if user has permission to add notes
    if not can_add_note(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only managers and admins can add coaching notes"
        )

    # Get session with user relationship eagerly loaded
    session_result = await db.execute(
        select(Session)
        .where(Session.id == session_id)
        .options(selectinload(Session.user))
    )
    session = session_result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    # Check if user can view this session
    if not can_view_session(current_user, session):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to add notes to this session"
        )

    # Create note
    note = ManagerNote(
        session_id=session_id,
        manager_id=current_user.id,
        note_text=note_data.note_text,
        is_edited=False
    )

    db.add(note)
    await db.commit()
    await db.refresh(note)

    logger.info(f"Manager {current_user.id} ({current_user.email}) added note to session {session_id}")

    # TODO: Send notification to session owner (rep)
    # This will be implemented in the notification system

    # Prepare response with manager name
    response = ManagerNoteResponse.model_validate(note)
    response.manager_name = f"{current_user.first_name or ''} {current_user.last_name or ''}".strip() or current_user.email

    return response


@router.post("/{session_id}/notes/audio", response_model=ManagerNoteResponse, status_code=status.HTTP_201_CREATED)
async def create_audio_manager_note(
    session_id: int,
    audio_file: UploadFile = File(...),
    duration: Optional[int] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new audio manager note on a session

    **Permissions:**
    - MANAGER: Can add audio notes to sessions in their team
    - ADMIN: Can add audio notes to any session in their organization
    - SYSTEM_ADMIN: Can add audio notes to any session
    - REP: Cannot add notes

    **Audio Requirements:**
    - Formats: webm, mp3, m4a, wav, ogg
    - Max size: 10MB
    - Max duration: 5 minutes (300 seconds)
    """
    # Check if user has permission to add notes
    if not can_add_note(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only managers and admins can add coaching notes"
        )

    # Get session with user relationship eagerly loaded
    session_result = await db.execute(
        select(Session)
        .where(Session.id == session_id)
        .options(selectinload(Session.user))
    )
    session = session_result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    # Check if user can view this session
    if not can_view_session(current_user, session):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to add notes to this session"
        )

    # Validate audio file
    if not audio_file.content_type or not audio_file.content_type.startswith("audio/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Expected audio file, got {audio_file.content_type}"
        )

    # Read file content
    file_content = await audio_file.read()
    file_size = len(file_content)

    # Validate file size (10MB max)
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size is 10MB, got {file_size / 1024 / 1024:.2f}MB"
        )

    try:
        from app.services.s3_service import get_s3_service
        from app.core.config import settings
        import tempfile

        # Determine file extension
        extension = audio_file.filename.split('.')[-1] if '.' in audio_file.filename else 'webm'

        # Generate file path
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        file_name = f"note_{current_user.id}_{session_id}_{timestamp}.{extension}"
        s3_key = f"manager_notes/{current_user.id}/{session_id}/{file_name}"

        # Save to temporary file first (same pattern as uploads.py)
        temp_file_path = None
        s3_url = None
        storage_type = None

        try:
            # Write to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{extension}") as temp_file:
                temp_file.write(file_content)
                temp_file_path = temp_file.name
                logger.info(f"Temporary file created for manager note: {temp_file_path}")

            # Upload to S3 if enabled
            if settings.AWS_S3_BUCKET_NAME and settings.AWS_ACCESS_KEY_ID:
                try:
                    s3_service = get_s3_service()
                    s3_url = s3_service.upload_file(
                        temp_file_path,
                        s3_key,
                        content_type=audio_file.content_type,
                    )
                    storage_type = "s3"
                    logger.info(f"Manager note uploaded to S3: {s3_url}")
                except Exception as e:
                    logger.warning(f"S3 upload failed, using local storage: {e}")
                    # Fallback to local storage
                    upload_dir = os.path.join("uploads", "manager_notes", str(current_user.id), str(session_id))
                    os.makedirs(upload_dir, exist_ok=True)

                    local_file_path = os.path.join(upload_dir, file_name)
                    import shutil
                    shutil.copy(temp_file_path, local_file_path)

                    storage_type = "local"
                    s3_url = f"manager_notes/{current_user.id}/{session_id}/{file_name}"
                    logger.info(f"Saved manager note locally: {local_file_path}")
            else:
                # Local storage (development mode)
                upload_dir = os.path.join("uploads", "manager_notes", str(current_user.id), str(session_id))
                os.makedirs(upload_dir, exist_ok=True)

                local_file_path = os.path.join(upload_dir, file_name)
                import shutil
                shutil.copy(temp_file_path, local_file_path)

                storage_type = "local"
                s3_url = f"manager_notes/{current_user.id}/{session_id}/{file_name}"
                logger.info(f"Saved manager note locally: {local_file_path}")

        finally:
            # Clean up temporary file
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                except Exception as e:
                    logger.warning(f"Failed to delete temporary file {temp_file_path}: {str(e)}")

        # Create audio note record
        note = ManagerNote(
            session_id=session_id,
            manager_id=current_user.id,
            note_type=NoteType.AUDIO,
            note_text=None,  # No text for audio notes
            is_edited=False,
            audio_s3_bucket=settings.AWS_S3_BUCKET_NAME if storage_type == "s3" else None,
            audio_s3_key=s3_key if storage_type == "s3" else s3_url,  # S3 key or local path
            audio_file_size=file_size,
            audio_duration=duration  # Duration from frontend
        )

        db.add(note)
        await db.commit()
        await db.refresh(note)

        logger.info(f"Manager {current_user.id} ({current_user.email}) added audio note to session {session_id}")

        # Prepare response with manager name and audio URL
        response = ManagerNoteResponse.model_validate(note)
        response.manager_name = f"{current_user.first_name or ''} {current_user.last_name or ''}".strip() or current_user.email
        response.audio_url = get_audio_url(note)

        return response

    except Exception as e:
        logger.error(f"Error creating audio note: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create audio note: {str(e)}"
        )


@router.get("/{session_id}/notes", response_model=ManagerNoteListResponse)
async def get_session_notes(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all notes for a session

    **Permissions:**
    - REP: Can view notes on their own sessions
    - MANAGER: Can view notes on sessions in their team
    - ADMIN: Can view notes on any session in their organization
    - SYSTEM_ADMIN: Can view all notes
    """
    # Get session with user relationship eagerly loaded
    session_result = await db.execute(
        select(Session)
        .where(Session.id == session_id)
        .options(selectinload(Session.user))
    )
    session = session_result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    # Check if user can view this session
    if not can_view_session(current_user, session):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view notes on this session"
        )

    # Get all notes for this session
    notes_result = await db.execute(
        select(ManagerNote)
        .where(ManagerNote.session_id == session_id)
        .order_by(ManagerNote.created_at.desc())
    )
    notes = notes_result.scalars().all()

    # Get manager info for each note
    manager_ids = [note.manager_id for note in notes]
    managers_result = await db.execute(
        select(User).where(User.id.in_(manager_ids))
    )
    managers = {m.id: m for m in managers_result.scalars().all()}

    # Build response
    note_responses = []
    for note in notes:
        note_response = ManagerNoteResponse.model_validate(note)
        manager = managers.get(note.manager_id)
        if manager:
            note_response.manager_name = f"{manager.first_name or ''} {manager.last_name or ''}".strip() or manager.email

        # Add audio URL for audio notes
        if note.note_type == NoteType.AUDIO:
            note_response.audio_url = get_audio_url(note)

        note_responses.append(note_response)

    return ManagerNoteListResponse(
        session_id=session_id,
        notes=note_responses,
        total_notes=len(note_responses)
    )


@router.put("/notes/{note_id}", response_model=ManagerNoteResponse)
async def update_manager_note(
    note_id: int,
    note_data: ManagerNoteUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update an existing manager note

    **Permissions:**
    - Only the manager who created the note can edit it
    - ADMIN can edit any note in their organization
    - SYSTEM_ADMIN can edit any note
    """
    # Get note with manager relationship eagerly loaded
    note_result = await db.execute(
        select(ManagerNote)
        .where(ManagerNote.id == note_id)
        .options(selectinload(ManagerNote.manager))
    )
    note = note_result.scalar_one_or_none()

    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found"
        )

    # Check permissions
    can_edit = (
        note.manager_id == current_user.id or  # Original author
        current_user.role == UserRole.SYSTEM_ADMIN or  # System admin
        (current_user.role == UserRole.ADMIN and  # Org admin (same org as note author)
         note.manager.organization_id == current_user.organization_id)
    )

    if not can_edit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to edit this note"
        )

    # Update note
    note.note_text = note_data.note_text
    note.is_edited = True

    await db.commit()
    await db.refresh(note)

    logger.info(f"Manager {current_user.id} updated note {note_id}")

    # Prepare response
    response = ManagerNoteResponse.model_validate(note)
    manager = await db.get(User, note.manager_id)
    if manager:
        response.manager_name = f"{manager.first_name or ''} {manager.last_name or ''}".strip() or manager.email

    return response


@router.delete("/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_manager_note(
    note_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a manager note

    **Permissions:**
    - Only the manager who created the note can delete it
    - ADMIN can delete any note in their organization
    - SYSTEM_ADMIN can delete any note
    """
    # Get note with manager relationship eagerly loaded
    note_result = await db.execute(
        select(ManagerNote)
        .where(ManagerNote.id == note_id)
        .options(selectinload(ManagerNote.manager))
    )
    note = note_result.scalar_one_or_none()

    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found"
        )

    # Check permissions
    can_delete = (
        note.manager_id == current_user.id or  # Original author
        current_user.role == UserRole.SYSTEM_ADMIN or  # System admin
        (current_user.role == UserRole.ADMIN and  # Org admin (same org as note author)
         note.manager.organization_id == current_user.organization_id)
    )

    if not can_delete:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this note"
        )

    # Delete note
    await db.delete(note)
    await db.commit()

    logger.info(f"Manager {current_user.id} deleted note {note_id}")

    return None
