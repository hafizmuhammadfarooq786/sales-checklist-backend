"""
Transcription API endpoints
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.session import Session, AudioFile, Transcript, SessionStatus
from app.api.dependencies import get_current_user_id
from app.services.transcription_dispatcher import schedule_transcription

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/{session_id}/transcribe", status_code=status.HTTP_202_ACCEPTED)
async def start_transcription(
    session_id: int,
    background_tasks: BackgroundTasks,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Start transcription for a session's audio file
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

    # Get audio file
    audio_result = await db.execute(
        select(AudioFile).where(AudioFile.session_id == session_id)
    )
    audio_file = audio_result.scalar_one_or_none()

    if not audio_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No audio file found for this session"
        )

    # Check if transcript already exists
    existing_transcript = await db.execute(
        select(Transcript).where(Transcript.session_id == session_id)
    )
    if existing_transcript.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Transcript already exists for this session"
        )

    session.status = SessionStatus.ANALYZING
    await db.commit()

    queue = schedule_transcription(session_id, audio_file.file_path, background_tasks)

    return {
        "message": "Transcription started",
        "session_id": session_id,
        "status": "processing",
        "queue": queue,
    }



@router.get("/{session_id}/transcript")
async def get_transcript(
    session_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Get transcript for a session
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

    # Get transcript
    transcript_result = await db.execute(
        select(Transcript).where(Transcript.session_id == session_id)
    )
    transcript = transcript_result.scalar_one_or_none()

    if not transcript:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transcript not found"
        )

    return {
        "session_id": session_id,
        "transcript": {
            "id": transcript.id,
            "text": transcript.text,
            "language": transcript.language,
            "duration_seconds": transcript.duration,
            "word_count": transcript.words_count,
            "created_at": transcript.created_at
        }
    }
