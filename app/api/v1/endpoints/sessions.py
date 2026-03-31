"""
Session API endpoints
"""
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.session import get_db
from app.models import Session, User
from app.models.session import SessionStatus, SessionMode
from app.models.scoring import ScoringResult, RiskBand
from app.schemas.session import (
    SessionCreate,
    SessionUpdate,
    SessionResponse,
    SessionListResponse,
    ManualChecklistSubmit,
)
from app.api.dependencies import (
    get_current_user_id,
    get_current_user,
    get_session_access_filter,
    check_session_access,
)

router = APIRouter()
logger = logging.getLogger(__name__)


async def generate_coaching_in_background(session_id: int, total_score: float, risk_band: RiskBand):
    """
    Background task to generate coaching feedback and report after checklist submission.
    """
    from app.db.session import get_db_session
    from app.models.scoring import CoachingFeedback
    from app.models.report import Report
    from app.models.checklist import ChecklistItem
    from app.services.coaching_service import get_coaching_service
    from app.services.report_service import get_report_service
    from sqlalchemy.orm import selectinload

    try:
        logger.info(f"Starting background coaching and report generation for session {session_id}")

        async with get_db_session() as db:
            # Get session
            session_result = await db.execute(
                select(Session).where(Session.id == session_id)
            )
            session = session_result.scalar_one_or_none()

            if not session:
                logger.error(f"Session {session_id} not found in background task")
                return

            # Get all responses for this session
            from app.models.session import SessionResponse as SessionResponseModel
            responses_result = await db.execute(
                select(SessionResponseModel)
                .where(SessionResponseModel.session_id == session_id)
                .options(selectinload(SessionResponseModel.item).selectinload(ChecklistItem.category))
            )
            responses = responses_result.scalars().all()

            # === Generate Coaching Feedback ===
            try:
                coaching_service = get_coaching_service()
                feedback_data = await coaching_service.generate_coaching_feedback(
                    session_id=session_id,
                    score=total_score,
                    risk_band=risk_band.value if hasattr(risk_band, 'value') else risk_band,
                    db=db,
                    customer_name=session.customer_name,
                    opportunity_name=session.opportunity_name or ""
                )

                # Check if coaching already exists
                existing_coaching_result = await db.execute(
                    select(CoachingFeedback).where(CoachingFeedback.session_id == session_id)
                )
                existing_coaching = existing_coaching_result.scalar_one_or_none()

                if existing_coaching:
                    # Update existing
                    existing_coaching.feedback_text = feedback_data['feedback_text']
                    existing_coaching.strengths = feedback_data.get('strengths')
                    existing_coaching.improvement_areas = feedback_data.get('improvement_areas')
                    existing_coaching.action_items = feedback_data.get('action_items')
                    existing_coaching.generated_at = datetime.utcnow()
                else:
                    # Create new
                    coaching_feedback = CoachingFeedback(
                        session_id=session_id,
                        feedback_text=feedback_data['feedback_text'],
                        strengths=feedback_data.get('strengths'),
                        improvement_areas=feedback_data.get('improvement_areas'),
                        action_items=feedback_data.get('action_items'),
                        generated_at=datetime.utcnow()
                    )
                    db.add(coaching_feedback)

                await db.commit()
                logger.info(f"Coaching feedback generated for session {session_id}")

            except Exception as coaching_error:
                logger.error(f"Failed to generate coaching for session {session_id}: {str(coaching_error)}", exc_info=True)

            # === Generate Report ===
            try:
                report_service = get_report_service()
                # Build report payload for the current ReportService API.
                category_scores = {}
                validated_count = 0
                responses_data = []
                for resp in responses:
                    item = resp.item
                    if not item or not item.category:
                        continue

                    cat_id = item.category.id
                    if cat_id not in category_scores:
                        category_scores[cat_id] = {
                            "name": item.category.name,
                            "score": 0,
                            "max_score": 0,
                        }
                    category_scores[cat_id]["max_score"] += 10

                    final_answer = (
                        resp.user_answer if resp.user_answer is not None else resp.ai_answer
                    )
                    if final_answer is True:
                        category_scores[cat_id]["score"] += 10
                        validated_count += 1

                    responses_data.append(
                        {
                            "id": resp.id,
                            "item_id": resp.item_id,
                            "is_validated": final_answer,
                            "ai_answer": resp.ai_answer,
                            "user_answer": resp.user_answer,
                            "item": {
                                "id": item.id,
                                "title": item.title or f"Checklist Item {item.id}",
                                "order": item.order,
                                "definition": item.definition or "",
                                "category": {
                                    "id": item.category.id,
                                    "name": item.category.name or "Uncategorized",
                                },
                            },
                        }
                    )

                scoring_data = {
                    "total_score": total_score,
                    "risk_band": risk_band.value if hasattr(risk_band, "value") else risk_band,
                    "category_scores": category_scores,
                    "top_strengths": [],
                    "top_gaps": [],
                    "items_validated": validated_count,
                    "items_total": len(responses),
                }

                session_data = {
                    "customer_name": session.customer_name,
                    "opportunity_name": session.opportunity_name,
                    "deal_stage": session.deal_stage,
                    "created_at": session.created_at,
                }

                pdf_result = await report_service.generate_session_report(
                    session_id=session_id,
                    user_id=session.user_id,
                    session_data=session_data,
                    scoring_data=scoring_data,
                    coaching_data=None,
                    responses_data=responses_data,
                )

                # Upsert reports table row so report endpoints can resolve it.
                report_result = await db.execute(
                    select(Report).where(Report.session_id == session_id)
                )
                existing_report = report_result.scalar_one_or_none()
                s3_key = pdf_result.get("s3_key") or pdf_result.get("pdf_url")
                if existing_report:
                    existing_report.pdf_s3_bucket = pdf_result.get("s3_bucket")
                    existing_report.pdf_s3_key = s3_key
                    existing_report.pdf_file_size = pdf_result.get("file_size")
                    existing_report.generated_at = datetime.utcnow()
                    existing_report.is_generated = True
                else:
                    db.add(
                        Report(
                            session_id=session_id,
                            pdf_s3_bucket=pdf_result.get("s3_bucket"),
                            pdf_s3_key=s3_key,
                            pdf_file_size=pdf_result.get("file_size"),
                            generated_at=datetime.utcnow(),
                            is_generated=True,
                        )
                    )
                await db.commit()
                logger.info(f"Report generated for session {session_id}")

            except Exception as report_error:
                logger.error(f"Failed to generate report for session {session_id}: {str(report_error)}", exc_info=True)

    except Exception as e:
        logger.error(f"Background task failed for session {session_id}: {str(e)}", exc_info=True)


# ============================================================================
# SESSION CRUD ENDPOINTS
# ============================================================================

@router.post("/", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    session_data: SessionCreate,
    current_user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new session.

    Two session modes:
    1. AUDIO: User records audio → AI transcribes & analyzes → User reviews
    2. MANUAL: User directly fills checklist (no audio/transcription)

    Session starts in DRAFT status.
    """
    # Create session (map API lowercase "audio"/"manual" to DB enum AUDIO/MANUAL)
    session_mode = SessionMode(session_data.session_mode.upper())
    session = Session(
        user_id=current_user_id,
        customer_name=session_data.customer_name,
        opportunity_name=session_data.opportunity_name,
        decision_influencer=session_data.decision_influencer,
        deal_stage=session_data.deal_stage,
        session_mode=session_mode,
        status=SessionStatus.DRAFT
    )

    db.add(session)
    await db.commit()
    await db.refresh(session)

    logger.info(f"Session {session.id} created by user {current_user_id} in {session_data.session_mode} mode")

    return SessionResponse.model_validate(session)


@router.get("/", response_model=SessionListResponse)
async def list_sessions(
    page: int = 1,
    page_size: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List sessions with RBAC filtering.

    RBAC:
    - REP: See only own sessions
    - MANAGER: See sessions from users in their team
    - ADMIN: See sessions from users in their organization
    - SYSTEM_ADMIN: See all sessions
    """
    skip = (page - 1) * page_size
    # Build query with role-based filter
    access_filter = get_session_access_filter(current_user)

    # Get sessions with user info
    from sqlalchemy.orm import selectinload

    query = (
        select(Session)
        .where(access_filter)
        .options(selectinload(Session.user))
        .order_by(Session.created_at.desc())
        .offset(skip)
        .limit(page_size)
    )

    result = await db.execute(query)
    sessions = result.scalars().all()

    # Get total count
    count_query = select(func.count(Session.id)).where(access_filter)
    count_result = await db.execute(count_query)
    total = count_result.scalar()

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
    Get a specific session.

    RBAC Applied:
    - REP: Can only view own sessions
    - MANAGER: Can view sessions from users in their team
    - ADMIN: Can view sessions from users in their organization
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
    Get checklist items with AI responses for review.

    Returns all 92 checklist items with:
    - AI answer (Yes/No)
    - AI reasoning
    - User override (if any)
    - Coaching questions for each item

    RBAC Applied:
    - REP: Can only view own session checklists
    - MANAGER: Can view checklists from users in their team
    - ADMIN: Can view checklists from users in their organization
    """
    # Check role-based access
    has_access = await check_session_access(session_id, current_user, db)

    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    # Get session
    session_result = await db.execute(
        select(Session).where(Session.id == session_id)
    )
    session = session_result.scalar_one_or_none()

    # Get all session responses with item details
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
            detail="No checklist responses found for this session. Please transcribe audio or fill checklist first."
        )

    # Format responses for review
    items_for_review = []
    total_score = 0
    items_yes = 0
    items_no = 0

    for response in responses:
        item = response.item

        # Use user answer if provided, otherwise AI answer
        final_answer = response.user_answer if response.user_answer is not None else response.ai_answer

        if final_answer:
            items_yes += 1
            total_score += 10
        else:
            items_no += 1

        # Get coaching questions for this item
        coaching_questions = [
            CoachingQuestionInfo(
                id=cq.id,
                section=cq.section,
                question=cq.question,
                order=cq.order
            )
            for cq in item.coaching_questions
        ]

        items_for_review.append(
            SessionResponseReview(
                item=ChecklistItemInfo(
                    id=item.id,
                    title=item.title,
                    definition=item.definition,
                    order=item.order
                ),
                ai_answer=response.ai_answer,
                ai_reasoning=response.ai_reasoning,
                user_answer=response.user_answer,
                was_changed=response.was_changed,
                score=response.score,
                coaching_questions=coaching_questions
            )
        )

    return ChecklistReviewResponse(
        session_id=session_id,
        customer_name=session.customer_name,
        opportunity_name=session.opportunity_name,
        items=items_for_review,
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


@router.post("/{session_id}/manual-checklist", response_model=SessionResponse)
async def submit_manual_checklist(
    session_id: int,
    checklist_data: ManualChecklistSubmit,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Submit manually filled checklist (for manual mode sessions)

    Workflow:
    1. Validate session is in manual mode
    2. Create SessionResponse records from manual input
    3. Calculate total score
    4. Update session status to completed
    5. Generate coaching feedback in background

    RBAC Applied:
    - REP: Can only submit own checklists
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

    # Get session
    session_result = await db.execute(
        select(Session).where(Session.id == session_id)
    )
    session = session_result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    # Validate session mode
    from app.models.session import SessionMode

    if session.session_mode != SessionMode.MANUAL:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "This endpoint is only for manual mode sessions",
                "current_mode": session.session_mode.value,
                "session_mode": session.session_mode.value
            }
        )

    # Check if already submitted
    from app.models.session import SessionResponse as SessionResponseModel

    existing_responses_result = await db.execute(
        select(SessionResponseModel).where(SessionResponseModel.session_id == session_id)
    )
    existing_responses = existing_responses_result.scalars().first()

    if existing_responses:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Checklist already submitted for this session"
        )

    # Create SessionResponse records from manual input
    response_records = []
    for item in checklist_data.responses:
        # Format notes for ai_reasoning field
        reasoning = f"Manual entry by user"
        if item.notes:
            reasoning += f". Notes: {item.notes}"

        response_record = SessionResponseModel(
            session_id=session_id,
            item_id=item.item_id,
            ai_answer=item.answer,  # In manual mode, user's answer is treated as "AI answer"
            ai_reasoning=reasoning,
            user_answer=None,  # No override needed since this IS the user's answer
            was_changed=False,
            score=10 if item.answer else 0
        )
        response_records.append(response_record)
        db.add(response_record)

    await db.commit()

    logger.info(f"Created {len(response_records)} manual responses for session {session_id}")

    # Calculate total score
    total_score = sum(r.score for r in response_records)

    # Determine risk band based on new thresholds
    # 70-100: Low Risk (Green)
    # 40-69: Medium Risk (Yellow)
    # 0-39: Critical Risk (Red)
    if total_score >= 70:
        risk_band = RiskBand.GREEN
    elif total_score >= 40:
        risk_band = RiskBand.YELLOW
    else:
        risk_band = RiskBand.RED

    # Create ScoringResult
    scoring_result = ScoringResult(
        session_id=session_id,
        total_score=total_score,
        risk_band=risk_band,
        items_validated=sum(1 for r in response_records if r.score > 0),
        items_total=len(response_records)
    )
    db.add(scoring_result)
    await db.flush()  # Get scoring_result.id for history
    await db.refresh(scoring_result)

    # Build responses snapshot for version history
    responses_snapshot = [
        {
            "item_id": r.item_id,
            "answer": r.ai_answer,  # In manual mode, ai_answer IS the user's answer
            "score": r.score
        }
        for r in response_records
    ]

    # Create score history record (next version number to avoid unique constraint)
    from app.models.scoring import ScoreHistory
    version_result = await db.execute(
        select(func.coalesce(func.max(ScoreHistory.version_number), 0)).where(
            ScoreHistory.session_id == session_id
        )
    )
    next_version = (version_result.scalar() or 0) + 1
    score_history_entry = ScoreHistory(
        session_id=session_id,
        scoring_result_id=scoring_result.id,
        total_score=total_score,
        risk_band=risk_band,
        items_validated=sum(1 for r in response_records if r.score > 0),
        items_total=len(response_records),
        calculated_at=datetime.utcnow(),
        score_change=None,  # No previous version to compare
        trigger_event="initial_submission",
        created_by_user_id=current_user.id,
        version_number=next_version,
        changes_count=None,  # First version, no changes
        responses_snapshot=responses_snapshot
    )
    db.add(score_history_entry)

    # Update session status
    session.status = SessionStatus.COMPLETED
    session.submitted_at = datetime.utcnow()

    await db.commit()
    await db.refresh(session)

    logger.info(f"Session {session_id} scoring complete: {total_score} points, {risk_band.value} band (Version {next_version} created)")

    # Generate coaching feedback in background (without transcript)
    background_tasks.add_task(
        generate_coaching_in_background,
        session_id,
        total_score,
        risk_band
    )

    return session


@router.post("/{session_id}/checklist/submit", response_model=ChecklistSubmitResponse)
async def submit_checklist(
    session_id: int,
    background_tasks: BackgroundTasks,
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

    # Determine risk band based on score (new thresholds)
    # 70-100: Low Risk (Green)
    # 40-69: Medium Risk (Yellow)
    # 0-39: Critical Risk (Red)
    if total_score >= 70:
        risk_band = RiskBand.GREEN
    elif total_score >= 40:
        risk_band = RiskBand.YELLOW
    else:
        risk_band = RiskBand.RED

    # Create or update ScoringResult
    scoring_result_query = await db.execute(
        select(ScoringResult).where(ScoringResult.session_id == session_id)
    )
    scoring_result = scoring_result_query.scalar_one_or_none()

    if scoring_result:
        # Update existing
        scoring_result.total_score = total_score
        scoring_result.risk_band = risk_band
        scoring_result.items_validated = items_yes
        scoring_result.items_total = len(responses)
    else:
        # Create new
        scoring_result = ScoringResult(
            session_id=session_id,
            total_score=total_score,
            risk_band=risk_band,
            items_validated=items_yes,
            items_total=len(responses),
            category_scores={},  # Can be enhanced later
            top_strengths=[],  # Can be enhanced later
            top_gaps=[]  # Can be enhanced later
        )
        db.add(scoring_result)

    await db.flush()  # Get scoring_result.id for history
    await db.refresh(scoring_result)

    # Build responses snapshot for version history
    responses_snapshot = [
        {
            "item_id": r.item_id,
            "answer": r.user_answer if r.user_answer is not None else r.ai_answer,
            "score": r.score
        }
        for r in responses
    ]

    # Create score history record (next version number to avoid unique constraint)
    from app.models.scoring import ScoreHistory
    version_result = await db.execute(
        select(func.coalesce(func.max(ScoreHistory.version_number), 0)).where(
            ScoreHistory.session_id == session_id
        )
    )
    next_version = (version_result.scalar() or 0) + 1
    score_history_entry = ScoreHistory(
        session_id=session_id,
        scoring_result_id=scoring_result.id,
        total_score=total_score,
        risk_band=risk_band,
        items_validated=items_yes,
        items_total=len(responses),
        calculated_at=datetime.utcnow(),
        score_change=None,  # No previous version to compare
        trigger_event="initial_submission",
        created_by_user_id=current_user.id,
        version_number=next_version,
        changes_count=None,  # First version, no changes
        responses_snapshot=responses_snapshot
    )
    db.add(score_history_entry)

    # Update session status
    session.status = SessionStatus.COMPLETED
    session.submitted_at = datetime.utcnow()

    await db.commit()

    logger.info(f"Checklist submitted for session {session_id}")
    logger.info(f"Final score: {total_score}/100 ({items_yes} YES, {items_no} NO)")
    logger.info(f"Risk band: {risk_band.value} (Version {next_version} created)")

    # Generate coaching feedback synchronously for immediate return
    try:
        from app.services.coaching_service import get_coaching_service
        from app.models.scoring import CoachingFeedback

        coaching_service = get_coaching_service()

        # Generate gap-based coaching
        feedback_data = await coaching_service.generate_coaching_feedback(
            session_id=session_id,
            score=total_score,
            risk_band=risk_band.value if hasattr(risk_band, 'value') else risk_band,
            db=db,
            customer_name=session.customer_name,
            opportunity_name=session.opportunity_name or ""
        )

        # Check if coaching feedback already exists for this session
        existing_coaching_result = await db.execute(
            select(CoachingFeedback).where(CoachingFeedback.session_id == session_id)
        )
        existing_coaching = existing_coaching_result.scalar_one_or_none()

        if existing_coaching:
            # Update existing coaching feedback
            existing_coaching.feedback_text = feedback_data['feedback_text']
            existing_coaching.strengths = feedback_data.get('strengths')
            existing_coaching.improvement_areas = feedback_data.get('improvement_areas')
            existing_coaching.action_items = feedback_data.get('action_items')
            existing_coaching.generated_at = datetime.utcnow()
            coaching_feedback = existing_coaching
        else:
            # Create new coaching feedback record
            coaching_feedback = CoachingFeedback(
                session_id=session_id,
                feedback_text=feedback_data['feedback_text'],
                strengths=feedback_data.get('strengths'),
                improvement_areas=feedback_data.get('improvement_areas'),
                action_items=feedback_data.get('action_items'),
                generated_at=datetime.utcnow()
            )
            db.add(coaching_feedback)

        await db.commit()
        await db.refresh(coaching_feedback)

        logger.info(f"Coaching feedback generated for session {session_id}")

        # Queue PDF report generation in background
        # background_tasks.add_task(
        #     generate_report_in_background,
        #     session_id,
        #     total_score,
        #     risk_band
        # )

        return ChecklistSubmitResponse(
            session_id=session_id,
            total_score=total_score,
            items_yes=items_yes,
            items_no=items_no,
            submitted_at=session.submitted_at,
            coaching_feedback={
                "id": coaching_feedback.id,
                "feedback_text": coaching_feedback.feedback_text,
                "improvement_areas": coaching_feedback.improvement_areas,
                "action_items": coaching_feedback.action_items
            },
            message=f"Checklist submitted successfully! Score: {total_score}/100. Coaching feedback generated."
        )

    except Exception as coaching_error:
        logger.error(f"Coaching generation failed: {str(coaching_error)}", exc_info=True)

        # Return success for submission even if coaching fails
        return ChecklistSubmitResponse(
            session_id=session_id,
            total_score=total_score,
            items_yes=items_yes,
            items_no=items_no,
            submitted_at=session.submitted_at,
            message=f"Checklist submitted successfully! Score: {total_score}/100. Coaching generation failed - please retry via /coaching endpoint."
        )


@router.post("/{session_id}/checklist/resubmit")
async def resubmit_checklist(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Re-submit checklist after making edits to create a new version.

    This endpoint creates a new ScoreHistory record (version) with:
    - Complete snapshot of all current checklist responses
    - Updated score calculation
    - Change tracking from previous version

    Workflow:
    1. User edits checklist answers (via PUT /checklist/{item_id})
    2. User clicks "Save as New Version" → calls this endpoint
    3. System creates Version N with current state
    4. User can view version history to see progression

    RBAC Applied:
    - REP: Can only resubmit own checklists
    - MANAGER: Can resubmit team checklists
    - ADMIN: Can resubmit org checklists
    """
    # Check role-based access
    has_access = await check_session_access(session_id, current_user, db)

    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    # Get session
    session_result = await db.execute(
        select(Session).where(Session.id == session_id)
    )
    session = session_result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    # Verify session is completed
    if session.status != SessionStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only resubmit completed sessions"
        )

    # Get all current responses
    responses_result = await db.execute(
        select(SessionResponseModel).where(
            SessionResponseModel.session_id == session_id
        )
    )
    responses = responses_result.scalars().all()

    if not responses:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No checklist responses found for this session"
        )

    # Recalculate score from current responses
    total_score = 0
    items_validated = 0

    for response in responses:
        # Use user answer if provided, otherwise AI answer
        final_answer = response.user_answer if response.user_answer is not None else response.ai_answer
        if final_answer:
            total_score += 10
            items_validated += 1

    # Determine risk band
    if total_score >= 70:
        risk_band = RiskBand.GREEN
    elif total_score >= 40:
        risk_band = RiskBand.YELLOW
    else:
        risk_band = RiskBand.RED

    # Get previous version to calculate changes
    from app.models.scoring import ScoreHistory

    prev_history_result = await db.execute(
        select(ScoreHistory)
        .where(ScoreHistory.session_id == session_id)
        .order_by(ScoreHistory.version_number.desc())
        .limit(1)
    )
    prev_history = prev_history_result.scalar_one_or_none()

    if not prev_history:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No previous version found. Please submit checklist first."
        )

    previous_score = prev_history.total_score
    score_change = total_score - previous_score
    version_number = prev_history.version_number + 1

    # Calculate how many answers changed from previous version
    prev_answers = {r["item_id"]: r["answer"] for r in prev_history.responses_snapshot}
    current_answers = {
        r.item_id: (r.user_answer if r.user_answer is not None else r.ai_answer)
        for r in responses
    }
    changes_count = sum(
        1 for item_id, answer in current_answers.items()
        if prev_answers.get(item_id) != answer
    )

    # Update ScoringResult (delete old, create new)
    old_scoring_result = await db.execute(
        select(ScoringResult).where(ScoringResult.session_id == session_id)
    )
    old_scoring_obj = old_scoring_result.scalar_one_or_none()

    if old_scoring_obj:
        await db.delete(old_scoring_obj)
        await db.flush()

    new_scoring = ScoringResult(
        session_id=session_id,
        total_score=total_score,
        risk_band=risk_band,
        items_validated=items_validated,
        items_total=len(responses)
    )
    db.add(new_scoring)
    await db.flush()
    await db.refresh(new_scoring)

    # Build responses snapshot
    responses_snapshot = [
        {
            "item_id": r.item_id,
            "answer": r.user_answer if r.user_answer is not None else r.ai_answer,
            "score": r.score
        }
        for r in responses
    ]

    # Create new ScoreHistory (new version)
    score_history_entry = ScoreHistory(
        session_id=session_id,
        scoring_result_id=new_scoring.id,
        total_score=total_score,
        risk_band=risk_band,
        items_validated=items_validated,
        items_total=len(responses),
        calculated_at=datetime.utcnow(),
        score_change=score_change,
        trigger_event="resubmission",
        created_by_user_id=current_user.id,
        version_number=version_number,
        changes_count=changes_count,
        responses_snapshot=responses_snapshot
    )
    db.add(score_history_entry)
    await db.commit()

    logger.info(f"Session {session_id} resubmitted: Version {version_number}, Score {total_score}, {changes_count} changes")

    return {
        "message": f"Version {version_number} created successfully",
        "version_number": version_number,
        "total_score": total_score,
        "risk_band": risk_band.value,
        "changes_count": changes_count,
        "score_change": score_change,
        "previous_score": previous_score
    }
