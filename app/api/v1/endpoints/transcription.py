"""
Transcription API endpoints
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, Any

from app.db.session import get_db
from app.models.session import Session, AudioFile, Transcript, SessionResponse, SessionStatus
from app.models.checklist import ChecklistItem
from app.api.dependencies import get_current_user_id
from app.services.transcription_service import transcription_service
from app.core.config import settings

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

    # Update session status
    session.status = SessionStatus.ANALYZING
    await db.commit()

    # Start transcription in background
    background_tasks.add_task(
        process_transcription,
        session_id,
        audio_file.file_path
    )

    return {
        "message": "Transcription started",
        "session_id": session_id,
        "status": "processing"
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
            detail="Transcript not found for this session"
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


async def process_transcription(session_id: int, file_path: str):
    """
    Background task to process transcription

    New workflow:
    1. Check if file is on S3 and generate pre-signed URL if needed
    2. Download S3 file to temporary location if needed
    3. Transcribe audio using Whisper API
    4. Save transcript to database
    5. Analyze transcript using ChecklistAnalyzer (GPT-4) to generate Yes/No answers for all 10 items
    6. Save AI responses with reasoning
    7. Update session status to 'pending_review' (ready for user to review and override)
    """
    from app.db.session import get_db_session
    from app.services.checklist_analyzer import analyzer
    from app.services.s3_service import get_s3_service
    import tempfile
    import os
    import httpx
    from urllib.parse import urlparse

    temp_file_path = None

    try:
        logger.info(f"Processing transcription for session {session_id}")

        # Check if file_path is an S3 URL
        is_s3_url = file_path.startswith("https://") and "s3" in file_path and "amazonaws.com" in file_path

        if is_s3_url:
            logger.info(f"File is on S3, generating pre-signed URL and downloading...")

            # Extract S3 key from URL
            # URL formats:
            # - https://bucket-name.s3.region.amazonaws.com/key
            # - https://s3.region.amazonaws.com/bucket-name/key
            parsed_url = urlparse(file_path)
            s3_key = parsed_url.path.lstrip('/')

            # If using path-style URL (s3.region.amazonaws.com/bucket/key), remove bucket name from key
            if parsed_url.hostname and not parsed_url.hostname.startswith(settings.AWS_S3_BUCKET_NAME):
                # This is path-style, remove bucket name from path
                parts = s3_key.split('/', 1)
                if len(parts) > 1:
                    s3_key = parts[1]

            logger.info(f"Extracted S3 key: {s3_key}")

            # Generate pre-signed URL (valid for 1 hour)
            s3_service = get_s3_service()
            presigned_url = s3_service.generate_presigned_url(s3_key, expiration=3600)

            if not presigned_url:
                raise Exception(f"Failed to generate pre-signed URL for S3 key: {s3_key}")

            logger.info(f"Pre-signed URL generated successfully")

            # Download file to temporary location
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.get(presigned_url)
                response.raise_for_status()

                # Create temporary file with appropriate extension
                file_extension = os.path.splitext(s3_key)[1] or '.webm'
                with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
                    temp_file.write(response.content)
                    temp_file_path = temp_file.name

                logger.info(f"Downloaded S3 file to temporary location: {temp_file_path}")
                logger.info(f"File size: {len(response.content)} bytes")

            # Use temporary file for transcription
            transcription_file_path = temp_file_path
        else:
            # Local file, use as-is
            logger.info(f"File is local: {file_path}")
            transcription_file_path = file_path

        # Transcribe audio
        transcript_data = await transcription_service.transcribe_audio(transcription_file_path, session_id)

        # Save transcript
        transcript = Transcript(
            session_id=session_id,
            text=transcript_data["text"],
            language=transcript_data.get("language", "en"),
            duration=transcript_data.get("duration"),
            words_count=len(transcript_data["text"].split()),
            processing_time=30.0  # Placeholder
        )

        async with get_db_session() as db:
            db.add(transcript)
            await db.commit()
            await db.refresh(transcript)

            logger.info(f"Transcript saved ({len(transcript_data['text'])} characters)")

        # Analyze transcript with new ChecklistAnalyzer (10 Yes/No answers)
        logger.info(f"Analyzing transcript with AI for 10 checklist items...")
        async with get_db_session() as db:
            analysis_results = await analyzer.analyze_transcript(transcript_data["text"], db)

            logger.info(f"AI analysis completed for {len(analysis_results)} items")

            # Delete old empty responses if they exist
            from sqlalchemy import delete
            await db.execute(
                delete(SessionResponse).where(SessionResponse.session_id == session_id)
            )
            await db.commit()

            # Create new SessionResponse records with AI answers
            for item_id, result in analysis_results.items():
                ai_answer = result["answer"]
                score = 10 if ai_answer else 0

                response = SessionResponse(
                    session_id=session_id,
                    item_id=item_id,
                    ai_answer=ai_answer,
                    ai_reasoning=result["reasoning"],
                    user_answer=None,  # User hasn't reviewed yet
                    was_changed=False,
                    score=score,  # Initial score based on AI answer
                )
                db.add(response)
                logger.info(f"Item {item_id}: {'YES' if ai_answer else 'NO'} ({score} pts) - {result['reasoning'][:50]}...")

            # Update session status to pending_review
            # This indicates AI has filled the checklist, now waiting for user review
            session_obj = await db.get(Session, session_id)
            if session_obj:
                session_obj.status = "pending_review"

            await db.commit()

        logger.info(f"Transcription and AI analysis completed for session {session_id}")
        logger.info(f"Status: pending_review (ready for user to review AI answers)")

    except Exception as e:
        logger.error(f"Transcription failed for session {session_id}: {str(e)}", exc_info=True)

        # Update session to failed status
        try:
            async with get_db_session() as db:
                session_obj = await db.get(Session, session_id)
                if session_obj:
                    session_obj.status = "failed"
                await db.commit()
        except Exception as commit_error:
            logger.error(f"Failed to update session status: {str(commit_error)}", exc_info=True)

    finally:
        # Clean up temporary file if it was created
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
                logger.info(f"Cleaned up temporary file: {temp_file_path}")
            except Exception as cleanup_error:
                logger.warning(f"Failed to delete temporary file {temp_file_path}: {str(cleanup_error)}")