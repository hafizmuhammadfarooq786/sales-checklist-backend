"""
Session Response API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from pydantic import BaseModel

from app.db.session import get_db
from app.models.session import Session, SessionResponse
from app.models.checklist import ChecklistItem
from app.api.dependencies import get_current_user_id

router = APIRouter()


class ResponseUpdate(BaseModel):
    is_validated: bool | None = None
    manual_override: bool = True


@router.get("/{session_id}/responses")
async def get_session_responses(
    session_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get all checklist item responses for a session"""
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
        .options(
            selectinload(SessionResponse.item).selectinload(ChecklistItem.category)
        )
        .order_by(SessionResponse.item_id)
    )
    responses = result.scalars().all()

    return {
        "session_id": session_id,
        "total_items": len(responses),
        "responses": [
            {
                "id": r.id,
                "item_id": r.item_id,
                "is_validated": r.is_validated,
                "confidence": r.confidence,
                "evidence_text": r.evidence_text,
                "manual_override": r.manual_override,
                "item": {
                    "id": r.item.id,
                    "title": r.item.title,
                    "definition": r.item.definition,
                    "key_behavior": r.item.key_behavior,
                    "key_mindset": r.item.key_mindset,
                    "category": {
                        "id": r.item.category.id,
                        "name": r.item.category.name,
                        "description": r.item.category.description
                    }
                }
            } for r in responses
        ]
    }


@router.patch("/{session_id}/responses/{item_id}")
async def update_session_response(
    session_id: int,
    item_id: int,
    response_data: ResponseUpdate,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Update a session response (manual override)"""
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
    response.is_validated = response_data.is_validated
    response.manual_override = response_data.manual_override
    response.override_by_user_id = user_id

    await db.commit()
    await db.refresh(response)

    return {
        "id": response.id,
        "item_id": response.item_id,
        "is_validated": response.is_validated,
        "manual_override": response.manual_override,
        "message": "Response updated successfully"
    }


@router.post("/{session_id}/responses/initialize")
async def initialize_session_responses(
    session_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Initialize responses for all checklist items with null values"""
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

    # Check if responses already exist
    existing_responses_result = await db.execute(
        select(SessionResponse).where(SessionResponse.session_id == session_id)
    )
    existing_responses = existing_responses_result.scalars().all()
    
    # If responses already exist, don't reinitialize them
    if existing_responses:
        return {
            "session_id": session_id,
            "total_items": len(existing_responses),
            "message": f"Session already has {len(existing_responses)} responses, skipping initialization"
        }

    # Get all active checklist items
    items_result = await db.execute(
        select(ChecklistItem).where(ChecklistItem.is_active == True)
    )
    items = items_result.scalars().all()

    # Create empty responses for all items (only if none exist)
    created_responses = []
    for item in items:
        response = SessionResponse(
            session_id=session_id,
            item_id=item.id,
            is_validated=None,
            confidence=None,
            evidence_text=None,
            ai_reasoning=None,
            manual_override=False
        )
        db.add(response)
        created_responses.append(response)

    await db.commit()

    # Refresh all
    for response in created_responses:
        await db.refresh(response)

    return {
        "session_id": session_id,
        "total_items": len(created_responses),
        "message": f"Initialized {len(created_responses)} empty responses"
    }