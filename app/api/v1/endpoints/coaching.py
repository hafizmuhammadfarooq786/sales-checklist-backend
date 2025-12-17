"""
Coaching Feedback API endpoints
Generate and retrieve AI-powered coaching feedback with optional TTS audio
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime
from typing import Optional

from app.db.session import get_db
from app.models.session import Session, SessionStatus
from app.models.scoring import ScoringResult, CoachingFeedback
from app.api.dependencies import get_current_user_id
from app.services.coaching_service import get_coaching_service

router = APIRouter()
logger = logging.getLogger(__name__)


def get_audio_url(coaching: CoachingFeedback, request=None) -> Optional[str]:
    """
    Generate a presigned URL or accessible URL for coaching audio.

    Args:
        coaching: CoachingFeedback instance
        request: Optional FastAPI Request object to get base URL

    Returns:
        URL string if audio exists, None otherwise
    """
    if not coaching.audio_s3_key:
        return None

    from app.services.s3_service import get_s3_service
    from app.core.config import settings

    # If audio is stored in S3, generate presigned URL
    if coaching.audio_s3_bucket:
        try:
            s3_service = get_s3_service()
            presigned_url = s3_service.generate_presigned_url(
                coaching.audio_s3_key,
                expiration=3600,  # 1 hour
                bucket_name=coaching.audio_s3_bucket  # Pass the correct bucket
            )
            if presigned_url:
                return presigned_url
        except Exception as e:
            logger.warning(f"Failed to generate presigned URL for audio: {e}")
    
    # For local storage, construct full URL
    # Try to get base URL from request if available
    base_url = "http://localhost:8000"  # Default fallback
    if request:
        base_url = str(request.base_url).rstrip("/")
    elif hasattr(settings, "API_BASE_URL") and settings.API_BASE_URL:
        base_url = settings.API_BASE_URL.rstrip("/")
    
    # Construct the full URL for local files
    audio_path = coaching.audio_s3_key
    if not audio_path.startswith("http"):
        # Remove leading slash if present
        if audio_path.startswith("/"):
            audio_path = audio_path[1:]
        # Construct full URL
        return f"{base_url}/api/v1/uploads/{audio_path}"
    
    return audio_path


@router.post("/{session_id}/coaching", status_code=status.HTTP_201_CREATED)
async def generate_coaching_feedback(
    session_id: int,
    include_audio: bool = True,
    background_tasks: BackgroundTasks = None,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    request: Request = None,
):
    """
    Generate AI-powered coaching feedback for a session.

    Prerequisites:
    - Session must have scoring results (run /calculate first)

    Args:
        session_id: Session ID
        include_audio: Whether to generate TTS audio (default: True)

    Returns:
        Coaching feedback with personalized insights and action items
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

    # Check if coaching already exists
    existing_result = await db.execute(
        select(CoachingFeedback).where(CoachingFeedback.session_id == session_id)
    )
    existing = existing_result.scalar_one_or_none()

    if existing:
        # Return existing coaching feedback
        return {
            "session_id": session_id,
            "coaching_id": existing.id,
            "feedback_text": existing.feedback_text,
            "strengths": existing.strengths,
            "improvement_areas": existing.improvement_areas,
            "action_items": existing.action_items,
            "audio_url": get_audio_url(existing, request),
            "audio_duration": existing.audio_duration,
            "generated_at": existing.generated_at,
            "message": "Coaching feedback already exists"
        }

    # Get scoring results (required)
    scoring_result = await db.execute(
        select(ScoringResult).where(ScoringResult.session_id == session_id)
    )
    scoring = scoring_result.scalar_one_or_none()

    if not scoring:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session must be scored first. Use POST /sessions/{id}/calculate"
        )

    try:
        # Generate coaching feedback
        coaching_service = get_coaching_service()

        feedback_data = await coaching_service.generate_coaching_feedback(
            session_id=session_id,
            score=scoring.total_score,
            risk_band=scoring.risk_band.value if hasattr(scoring.risk_band, 'value') else scoring.risk_band,
            db=db,  # Pass database session for gap data fetching
            customer_name=session.customer_name,
            opportunity_name=session.opportunity_name or ""
        )

        # Generate audio if requested
        audio_data = None
        if include_audio and feedback_data.get('feedback_text'):
            audio_data = await coaching_service.generate_coaching_audio(
                feedback_text=feedback_data['feedback_text'],
                session_id=session_id,
                user_id=user_id
            )

        # Save to database
        coaching_feedback = CoachingFeedback(
            session_id=session_id,
            feedback_text=feedback_data['feedback_text'],
            strengths=feedback_data.get('strengths'),
            improvement_areas=feedback_data.get('improvement_areas'),
            action_items=feedback_data.get('action_items'),
            audio_s3_bucket=audio_data.get('s3_bucket') if audio_data else None,
            audio_s3_key=audio_data.get('s3_key') if audio_data else audio_data.get('audio_url') if audio_data else None,
            audio_duration=audio_data.get('duration_seconds') if audio_data else None,
            generated_at=datetime.utcnow()
        )

        db.add(coaching_feedback)
        await db.commit()
        await db.refresh(coaching_feedback)

        # Update session status
        session.status = SessionStatus.COMPLETED
        await db.commit()

        return {
            "session_id": session_id,
            "coaching_id": coaching_feedback.id,
            "feedback_text": coaching_feedback.feedback_text,
            "strengths": coaching_feedback.strengths,
            "improvement_areas": coaching_feedback.improvement_areas,
            "action_items": coaching_feedback.action_items,
            "audio_url": get_audio_url(coaching_feedback),
            "audio_duration": coaching_feedback.audio_duration,
            "generated_at": coaching_feedback.generated_at,
            "message": "Coaching feedback generated successfully"
        }

    except Exception as e:
        logger.error(f"Error generating coaching feedback for session {session_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate coaching feedback: {str(e)}"
        )


@router.get("/{session_id}/coaching")
async def get_coaching_feedback(
    session_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    request: Request = None,
):
    """
    Get existing coaching feedback for a session.

    Returns:
        Coaching feedback with personalized insights and action items
    """
    from app.services.s3_service import get_s3_service
    from app.core.config import settings
    
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

    # Get coaching feedback
    coaching_result = await db.execute(
        select(CoachingFeedback).where(CoachingFeedback.session_id == session_id)
    )
    coaching = coaching_result.scalar_one_or_none()

    if not coaching:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Coaching feedback not yet generated. It's being created in the background."
        )

    # Generate presigned URL for audio if it exists
    audio_url = get_audio_url(coaching, request)

    return {
        "session_id": session_id,
        "coaching_id": coaching.id,
        "feedback_text": coaching.feedback_text,
        "strengths": coaching.strengths,
        "improvement_areas": coaching.improvement_areas,
        "action_items": coaching.action_items,
        "audio_url": audio_url,
        "audio_duration": coaching.audio_duration,
        "generated_at": coaching.generated_at
    }


@router.post("/{session_id}/coaching/regenerate")
async def regenerate_coaching_feedback(
    session_id: int,
    include_audio: bool = True,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    request: Request = None,
):
    """
    Regenerate coaching feedback for a session (overwrites existing).

    Use this if you want fresh coaching insights after updating responses.
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

    # Delete existing coaching feedback
    existing_result = await db.execute(
        select(CoachingFeedback).where(CoachingFeedback.session_id == session_id)
    )
    existing = existing_result.scalar_one_or_none()

    if existing:
        await db.delete(existing)
        await db.commit()

    # Get scoring results
    scoring_result = await db.execute(
        select(ScoringResult).where(ScoringResult.session_id == session_id)
    )
    scoring = scoring_result.scalar_one_or_none()

    if not scoring:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session must be scored first"
        )

    try:
        coaching_service = get_coaching_service()

        feedback_data = await coaching_service.generate_coaching_feedback(
            session_id=session_id,
            score=scoring.total_score,
            risk_band=scoring.risk_band.value if hasattr(scoring.risk_band, 'value') else scoring.risk_band,
            db=db,  # Pass database session for gap data fetching
            customer_name=session.customer_name,
            opportunity_name=session.opportunity_name or ""
        )

        audio_data = None
        if include_audio and feedback_data.get('feedback_text'):
            audio_data = await coaching_service.generate_coaching_audio(
                feedback_text=feedback_data['feedback_text'],
                session_id=session_id,
                user_id=user_id
            )

        coaching_feedback = CoachingFeedback(
            session_id=session_id,
            feedback_text=feedback_data['feedback_text'],
            strengths=feedback_data.get('strengths'),
            improvement_areas=feedback_data.get('improvement_areas'),
            action_items=feedback_data.get('action_items'),
            audio_s3_bucket=audio_data.get('s3_bucket') if audio_data else None,
            audio_s3_key=audio_data.get('s3_key') if audio_data else audio_data.get('audio_url') if audio_data else None,
            audio_duration=audio_data.get('duration_seconds') if audio_data else None,
            generated_at=datetime.utcnow()
        )

        db.add(coaching_feedback)
        await db.commit()
        await db.refresh(coaching_feedback)

        return {
            "session_id": session_id,
            "coaching_id": coaching_feedback.id,
            "feedback_text": coaching_feedback.feedback_text,
            "strengths": coaching_feedback.strengths,
            "improvement_areas": coaching_feedback.improvement_areas,
            "action_items": coaching_feedback.action_items,
            "audio_url": get_audio_url(coaching_feedback, request),
            "audio_duration": coaching_feedback.audio_duration,
            "generated_at": coaching_feedback.generated_at,
            "message": "Coaching feedback regenerated successfully"
        }

    except Exception as e:
        logger.error(f"Error regenerating coaching feedback for session {session_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to regenerate coaching feedback: {str(e)}"
        )
