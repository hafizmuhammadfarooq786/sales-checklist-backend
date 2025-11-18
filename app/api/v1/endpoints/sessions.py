"""
Session API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List

from app.db.session import get_db
from app.models import Session, User
from app.models.session import SessionStatus
from app.schemas.session import (
    SessionCreate,
    SessionUpdate,
    SessionResponse,
    SessionListResponse,
)
from app.api.dependencies import get_current_user_id

router = APIRouter()


@router.post("/", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    session_data: SessionCreate,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new session.
    User ID should come from authenticated JWT token.
    """
    # Verify user exists
    user_result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Create session
    session = Session(
        user_id=user_id,
        customer_name=session_data.customer_name,
        opportunity_name=session_data.opportunity_name,
        decision_influencer=session_data.decision_influencer,
        deal_stage=session_data.deal_stage,
        status=SessionStatus.DRAFT,
    )

    db.add(session)
    await db.commit()
    await db.refresh(session)

    return SessionResponse.model_validate(session)


@router.get("/", response_model=SessionListResponse)
async def list_sessions(
    user_id: int = Depends(get_current_user_id),
    page: int = 1,
    page_size: int = 20,
    status_filter: SessionStatus = None,
    db: AsyncSession = Depends(get_db)
):
    """
    List sessions for the authenticated user with pagination.
    """
    # Build query
    query = select(Session).where(Session.user_id == user_id)

    if status_filter:
        query = query.where(Session.status == status_filter)

    query = query.order_by(Session.created_at.desc())

    # Get total count
    count_query = select(func.count()).select_from(Session).where(Session.user_id == user_id)
    if status_filter:
        count_query = count_query.where(Session.status == status_filter)

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    # Execute query
    result = await db.execute(query)
    sessions = result.scalars().all()

    return SessionListResponse(
        sessions=[SessionResponse.model_validate(s) for s in sessions],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific session by ID.
    User can only access their own sessions.
    """
    result = await db.execute(
        select(Session).where(
            Session.id == session_id,
            Session.user_id == user_id
        )
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    return SessionResponse.model_validate(session)


@router.patch("/{session_id}", response_model=SessionResponse)
async def update_session(
    session_id: int,
    session_data: SessionUpdate,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a session.
    User can only update their own sessions.
    """
    result = await db.execute(
        select(Session).where(
            Session.id == session_id,
            Session.user_id == user_id
        )
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    # Update fields
    update_data = session_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(session, field, value)

    await db.commit()
    await db.refresh(session)

    return SessionResponse.model_validate(session)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a session.
    User can only delete their own sessions.
    """
    result = await db.execute(
        select(Session).where(
            Session.id == session_id,
            Session.user_id == user_id
        )
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    await db.delete(session)
    await db.commit()

    return None
