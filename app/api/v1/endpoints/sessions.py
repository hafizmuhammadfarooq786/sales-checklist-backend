"""
Session API endpoints
"""
import logging
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
from app.api.dependencies import (
    get_current_user_id,
    get_current_user,
    get_session_access_filter,
    check_session_access,
)

router = APIRouter()
logger = logging.getLogger(__name__)


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

    # Note: SessionResponse records will be created automatically after transcription
    # The AI will analyze the transcript and fill in all 10 checklist items with Yes/No answers
    logger.info(f"Created session {session.id} for customer '{session.customer_name}'")
    logger.info(f"Next steps: Upload audio → Transcribe → AI auto-fills checklist → User reviews")

    return SessionResponse.model_validate(session)


@router.get("/", response_model=SessionListResponse)
async def list_sessions(
    current_user: User = Depends(get_current_user),
    page: int = 1,
    page_size: int = 20,
    status_filter: SessionStatus = None,
    db: AsyncSession = Depends(get_db)
):
    """
    List sessions for the authenticated user with pagination.

    RBAC Applied:
    - REP: See only own sessions
    - MANAGER: See all sessions from users in their team
    - ADMIN: See all sessions from users in their organization
    """
    # Build role-based access filter
    access_filter = get_session_access_filter(current_user)

    # Build query with RBAC filter
    query = select(Session).where(access_filter)

    if status_filter:
        query = query.where(Session.status == status_filter)

    query = query.order_by(Session.created_at.desc())

    # Get total count with RBAC filter
    count_query = select(func.count()).select_from(Session).where(access_filter)
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific session by ID.

    RBAC Applied:
    - REP: Can only access own sessions
    - MANAGER: Can access sessions from users in their team
    - ADMIN: Can access sessions from users in their organization
    """
    # Check role-based access
    has_access = await check_session_access(session_id, current_user, db)

    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    # Fetch the session
    result = await db.execute(
        select(Session).where(Session.id == session_id)
    )
    session = result.scalar_one_or_none()

    return SessionResponse.model_validate(session)


@router.patch("/{session_id}", response_model=SessionResponse)
async def update_session(
    session_id: int,
    session_data: SessionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a session.

    RBAC Applied:
    - REP: Can only update own sessions
    - MANAGER: Can update sessions from users in their team
    - ADMIN: Can update sessions from users in their organization
    """
    # Check role-based access
    has_access = await check_session_access(session_id, current_user, db)

    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    # Fetch the session
    result = await db.execute(
        select(Session).where(Session.id == session_id)
    )
    session = result.scalar_one_or_none()

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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a session.

    RBAC Applied:
    - REP: Can only delete own sessions
    - MANAGER: Can delete sessions from users in their team
    - ADMIN: Can delete sessions from users in their organization
    """
    # Check role-based access
    has_access = await check_session_access(session_id, current_user, db)

    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    # Fetch the session
    result = await db.execute(
        select(Session).where(Session.id == session_id)
    )
    session = result.scalar_one_or_none()

    await db.delete(session)
    await db.commit()

    return None


# ============================================================================
# NEW CHECKLIST REVIEW ENDPOINTS (10-item AI auto-fill system)
# ============================================================================

from app.schemas.checklist import (
    ChecklistReviewResponse,
    SessionResponseReview,
    ChecklistItemInfo,
    CoachingQuestionInfo,
    ChecklistItemUpdate,
    ChecklistItemUpdateResponse,
    ChecklistSubmitResponse,
)
from app.models.checklist import ChecklistItem, ChecklistCategory, CoachingQuestion
from app.models.session import SessionResponse as SessionResponseModel
from datetime import datetime


@router.get("/{session_id}/checklist", response_model=ChecklistReviewResponse)
async def get_checklist_for_review(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get AI-filled checklist for user review.

    Returns all 10 checklist items with:
    - AI answers (Yes/No with reasoning)
    - User overrides (if any)
    - Coaching questions for each item
    - Current score (0-100)

    This is the page where user reviews AI answers and can manually change them.

    RBAC Applied:
    - REP: Can only access own session checklists
    - MANAGER: Can access checklists from users in their team
    - ADMIN: Can access checklists from users in their organization
    """
    # Check role-based access
    has_access = await check_session_access(session_id, current_user, db)

    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    # Fetch the session
    session_result = await db.execute(
        select(Session).where(Session.id == session_id)
    )
    session = session_result.scalar_one_or_none()

    # Get all session responses with items and coaching questions
    from sqlalchemy.orm import selectinload

    responses_result = await db.execute(
        select(SessionResponseModel)
        .where(SessionResponseModel.session_id == session_id)
        .options(
            selectinload(SessionResponseModel.item).selectinload(ChecklistItem.category),
            selectinload(SessionResponseModel.item).selectinload(ChecklistItem.coaching_questions)
        )
        .order_by(SessionResponseModel.item_id)
    )
    responses = responses_result.scalars().all()

    if not responses:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Checklist not yet generated. Please transcribe the audio first."
        )

    # Build response items
    items_list = []
    total_score = 0
    items_yes = 0
    items_no = 0

    for response in responses:
        # Determine current answer (user override takes precedence)
        current_answer = response.user_answer if response.user_answer is not None else response.ai_answer

        if current_answer:
            items_yes += 1
            total_score += 10
        else:
            items_no += 1

        # Build item info
        item_info = ChecklistItemInfo(
            id=response.item.id,
            title=response.item.title,
            definition=response.item.definition,
            key_behavior=response.item.key_behavior,
            order=response.item.order
        )

        # Build coaching questions
        coaching_questions_list = [
            CoachingQuestionInfo(
                id=q.id,
                section=q.section,
                question=q.question,
                order=q.order
            )
            for q in response.item.coaching_questions if q.is_active
        ]

        # Build session response review
        session_response_review = SessionResponseReview(
            item=item_info,
            ai_answer=response.ai_answer,
            ai_reasoning=response.ai_reasoning or "No reasoning provided",
            user_answer=response.user_answer,
            was_changed=response.was_changed,
            score=response.score,
            coaching_questions=coaching_questions_list
        )

        items_list.append(session_response_review)

    return ChecklistReviewResponse(
        session_id=session_id,
        customer_name=session.customer_name,
        opportunity_name=session.opportunity_name,
        items=items_list,
        total_score=total_score,
        items_yes=items_yes,
        items_no=items_no,
        status=session.status.value
    )


@router.put(
    "/{session_id}/checklist/{item_id}",
    response_model=ChecklistItemUpdateResponse
)
async def update_checklist_item(
    session_id: int,
    item_id: int,
    update_data: ChecklistItemUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a single checklist item (manual override).

    Allows the user to change the AI's answer before submitting.
    Updates the user_answer, was_changed flag, and recalculates score.

    RBAC Applied:
    - REP: Can only update own session checklists
    - MANAGER: Can update checklists from users in their team
    - ADMIN: Can update checklists from users in their organization
    """
    # Check role-based access
    has_access = await check_session_access(session_id, current_user, db)

    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    # Get the session response
    response_result = await db.execute(
        select(SessionResponseModel).where(
            SessionResponseModel.session_id == session_id,
            SessionResponseModel.item_id == item_id
        )
    )
    response = response_result.scalar_one_or_none()

    if not response:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Checklist item not found"
        )

    # Update user answer
    response.user_answer = update_data.user_answer
    response.was_changed = (response.user_answer != response.ai_answer)
    response.changed_at = datetime.utcnow() if response.was_changed else None

    # Recalculate score based on final answer
    final_answer = response.user_answer if response.user_answer is not None else response.ai_answer
    response.score = 10 if final_answer else 0

    await db.commit()
    await db.refresh(response)

    logger.info(f"Item {item_id} updated: AI={response.ai_answer}, User={response.user_answer}, Score={response.score}")

    return ChecklistItemUpdateResponse(
        item_id=item_id,
        ai_answer=response.ai_answer,
        user_answer=response.user_answer,
        was_changed=response.was_changed,
        score=response.score,
        message="Checklist item updated successfully"
    )


@router.post("/{session_id}/checklist/submit", response_model=ChecklistSubmitResponse)
async def submit_checklist(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Submit finalized checklist to coach for review.

    This endpoint:
    1. Calculates final total score
    2. Updates session status to 'submitted'
    3. Records submitted_at timestamp
    4. (Future) Creates CustomerChecklist record for tracking over time

    After submission, the coach can review the results.

    RBAC Applied:
    - REP: Can only submit own session checklists
    - MANAGER: Can submit checklists from users in their team
    - ADMIN: Can submit checklists from users in their organization
    """
    # Check role-based access
    has_access = await check_session_access(session_id, current_user, db)

    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    # Fetch the session
    session_result = await db.execute(
        select(Session).where(Session.id == session_id)
    )
    session = session_result.scalar_one_or_none()

    # Get all session responses
    responses_result = await db.execute(
        select(SessionResponseModel).where(
            SessionResponseModel.session_id == session_id
        )
    )
    responses = responses_result.scalars().all()

    if not responses:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No checklist responses found. Please transcribe the audio first."
        )

    # Calculate final scores
    total_score = 0
    items_yes = 0
    items_no = 0

    for response in responses:
        # Use user answer if provided, otherwise AI answer
        final_answer = response.user_answer if response.user_answer is not None else response.ai_answer

        if final_answer:
            items_yes += 1
            total_score += 10
        else:
            items_no += 1

    # Update session status
    session.status = SessionStatus.SUBMITTED
    session.submitted_at = datetime.utcnow()

    await db.commit()

    logger.info(f"Checklist submitted for session {session_id}")
    logger.info(f"Final score: {total_score}/100 ({items_yes} YES, {items_no} NO)")

    return ChecklistSubmitResponse(
        session_id=session_id,
        total_score=total_score,
        items_yes=items_yes,
        items_no=items_no,
        submitted_at=session.submitted_at,
        message=f"Checklist submitted successfully! Score: {total_score}/100"
    )
