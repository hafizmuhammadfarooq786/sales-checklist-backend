"""
Manager Notes API endpoints - Coaching feedback system
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload
from typing import List

from app.db.session import get_db
from app.models.manager_note import ManagerNote
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
