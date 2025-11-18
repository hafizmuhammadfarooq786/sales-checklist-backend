"""
Session Response API endpoints
Handles checklist item responses (Yes/No/Partial) for each session
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List

from app.db.session import get_db
from app.models import Session, SessionResponse, ChecklistItem
from app.models.session import SessionStatus
from app.schemas.response import (
    SessionResponseCreate,
    SessionResponseUpdate,
    SessionResponseOut,
    BulkResponseCreate,
    SessionResponseListOut,
)
from app.api.dependencies import get_current_user_id

router = APIRouter()


@router.get("/{session_id}/responses", response_model=SessionResponseListOut)
async def get_session_responses(
    session_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all checklist item responses for a session
    """
    # Verify session belongs to user
    session_result = await db.execute(
        select(Session).where(
            Session.id == session_id,
            Session.user_id == user_id,
        )
    )
    session = session_result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    # Get all responses with checklist item details
    result = await db.execute(
        select(SessionResponse)
        .where(SessionResponse.session_id == session_id)
        .options(selectinload(SessionResponse.item))
        .order_by(SessionResponse.item_id)
    )
    responses = result.scalars().all()

    return SessionResponseListOut(
        session_id=session_id,
        total_items=len(responses),
        responses=[SessionResponseOut.model_validate(r) for r in responses]
    )


@router.post("/{session_id}/responses", response_model=SessionResponseOut, status_code=status.HTTP_201_CREATED)
async def create_session_response(
    session_id: int,
    response_data: SessionResponseCreate,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a single session response for a checklist item
    """
    # Verify session belongs to user
    session_result = await db.execute(
        select(Session).where(
            Session.id == session_id,
            Session.user_id == user_id,
        )
    )
    session = session_result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    # Verify checklist item exists
    item_result = await db.execute(
        select(ChecklistItem).where(ChecklistItem.id == response_data.item_id)
    )
    item = item_result.scalar_one_or_none()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Checklist item {response_data.item_id} not found"
        )

    # Check if response already exists
    existing_result = await db.execute(
        select(SessionResponse).where(
            SessionResponse.session_id == session_id,
            SessionResponse.item_id == response_data.item_id
        )
    )
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Response for item {response_data.item_id} already exists. Use PATCH to update."
        )

    # Create response
    response = SessionResponse(
        session_id=session_id,
        **response_data.model_dump()
    )

    db.add(response)
    await db.commit()
    await db.refresh(response)

    return SessionResponseOut.model_validate(response)


@router.post("/{session_id}/responses/bulk", response_model=SessionResponseListOut)
async def bulk_create_responses(
    session_id: int,
    bulk_data: BulkResponseCreate,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Bulk create responses for all checklist items in a session
    Useful for initializing a session with empty responses or AI-generated responses
    """
    # Verify session belongs to user
    session_result = await db.execute(
        select(Session).where(
            Session.id == session_id,
            Session.user_id == user_id,
        )
    )
    session = session_result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    # Delete existing responses (if any)
    await db.execute(
        select(SessionResponse).where(SessionResponse.session_id == session_id)
    )

    # Create all responses
    created_responses = []
    for response_data in bulk_data.responses:
        response = SessionResponse(
            session_id=session_id,
            **response_data.model_dump()
        )
        db.add(response)
        created_responses.append(response)

    await db.commit()

    # Refresh all responses
    for response in created_responses:
        await db.refresh(response)

    return SessionResponseListOut(
        session_id=session_id,
        total_items=len(created_responses),
        responses=[SessionResponseOut.model_validate(r) for r in created_responses]
    )


@router.patch("/{session_id}/responses/{item_id}", response_model=SessionResponseOut)
async def update_session_response(
    session_id: int,
    item_id: int,
    response_data: SessionResponseUpdate,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a session response (for manual overrides or AI updates)
    """
    # Verify session belongs to user
    session_result = await db.execute(
        select(Session).where(
            Session.id == session_id,
            Session.user_id == user_id,
        )
    )
    session = session_result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    # Get existing response
    result = await db.execute(
        select(SessionResponse).where(
            SessionResponse.session_id == session_id,
            SessionResponse.item_id == item_id
        )
    )
    response = result.scalar_one_or_none()

    if not response:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Response for item {item_id} not found in this session"
        )

    # Update fields
    update_data = response_data.model_dump(exclude_unset=True)

    # If manual_override is being set, record who did it
    if update_data.get("manual_override"):
        update_data["override_by_user_id"] = user_id

    for field, value in update_data.items():
        setattr(response, field, value)

    await db.commit()
    await db.refresh(response)

    return SessionResponseOut.model_validate(response)


@router.delete("/{session_id}/responses/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session_response(
    session_id: int,
    item_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a session response
    """
    # Verify session belongs to user
    session_result = await db.execute(
        select(Session).where(
            Session.id == session_id,
            Session.user_id == user_id,
        )
    )
    session = session_result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    # Get existing response
    result = await db.execute(
        select(SessionResponse).where(
            SessionResponse.session_id == session_id,
            SessionResponse.item_id == item_id
        )
    )
    response = result.scalar_one_or_none()

    if not response:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Response for item {item_id} not found"
        )

    await db.delete(response)
    await db.commit()

    return None


@router.post("/{session_id}/responses/initialize", response_model=SessionResponseListOut)
async def initialize_session_responses(
    session_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Initialize responses for all checklist items with null values
    Useful for creating a blank checklist for manual filling
    """
    # Verify session belongs to user
    session_result = await db.execute(
        select(Session).where(
            Session.id == session_id,
            Session.user_id == user_id,
        )
    )
    session = session_result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    # Get all active checklist items
    items_result = await db.execute(
        select(ChecklistItem).where(ChecklistItem.is_active == True)
    )
    items = items_result.scalars().all()

    # Delete existing responses
    await db.execute(
        select(SessionResponse).where(SessionResponse.session_id == session_id)
    )

    # Create empty responses for all items
    created_responses = []
    for item in items:
        response = SessionResponse(
            session_id=session_id,
            item_id=item.id,
            is_validated=None,  # Empty - to be filled manually or by AI
            confidence=None,
            evidence_text=None,
            ai_reasoning=None,
        )
        db.add(response)
        created_responses.append(response)

    await db.commit()

    # Refresh all
    for response in created_responses:
        await db.refresh(response)

    return SessionResponseListOut(
        session_id=session_id,
        total_items=len(created_responses),
        responses=[SessionResponseOut.model_validate(r) for r in created_responses]
    )
