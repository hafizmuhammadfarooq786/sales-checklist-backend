"""
Transcription + AI checklist analysis pipeline.

Used by FastAPI BackgroundTasks and by Celery workers (via asyncio.run).
"""
import logging
import os
from io import BytesIO
from urllib.parse import urlparse

import boto3
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import delete

from app.core.config import settings
from app.db.session import get_db_session
from app.models.session import Session, SessionResponse, SessionStatus, Transcript
from app.services.checklist_analyzer import analyzer
from app.services.transcription_service import transcription_service

logger = logging.getLogger(__name__)


async def run_transcription_job(session_id: int, file_path: str) -> None:
    """
    Full pipeline: load audio (S3 or local), Whisper, persist transcript,
    GPT checklist analysis, session -> pending_review (or failed).
    """
    try:
        logger.info("Processing transcription for session %s", session_id)

        is_s3_url = (
            file_path.startswith("https://")
            and "s3" in file_path
            and "amazonaws.com" in file_path
        )

        if is_s3_url:
            logger.info("File is on S3, streaming directly to memory...")
            parsed_url = urlparse(file_path)
            s3_key = parsed_url.path.lstrip("/")
            if parsed_url.hostname and not parsed_url.hostname.startswith(
                settings.AWS_S3_BUCKET_NAME
            ):
                parts = s3_key.split("/", 1)
                if len(parts) > 1:
                    s3_key = parts[1]

            logger.info("Extracted S3 key: %s", s3_key)

            s3_client = boto3.client(
                "s3",
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION,
            )

            file_buffer = BytesIO()
            await run_in_threadpool(
                s3_client.download_fileobj,
                settings.AWS_S3_BUCKET_NAME,
                s3_key,
                file_buffer,
            )
            file_buffer.seek(0)

            file_size = file_buffer.seek(0, 2)
            file_buffer.seek(0)
            logger.info("Streamed S3 file to memory: %s bytes", file_size)

            filename = os.path.basename(s3_key)
            transcript_data = await transcription_service.transcribe_audio(
                file_buffer,
                session_id,
                filename=filename,
            )
        else:
            logger.info("File is local: %s", file_path)
            transcript_data = await transcription_service.transcribe_audio(
                file_path, session_id
            )

        transcript = Transcript(
            session_id=session_id,
            text=transcript_data["text"],
            language=transcript_data.get("language", "en"),
            duration=transcript_data.get("duration"),
            words_count=len(transcript_data["text"].split()),
            processing_time=30.0,
        )

        async with get_db_session() as db:
            db.add(transcript)
            await db.commit()
            await db.refresh(transcript)
            logger.info(
                "Transcript saved (%s characters)", len(transcript_data["text"])
            )

        logger.info("Analyzing transcript with AI for 10 checklist items...")
        async with get_db_session() as db:
            analysis_results = await analyzer.analyze_transcript(
                transcript_data["text"], db, session_id
            )
            logger.info("AI analysis completed for %s items", len(analysis_results))

            await db.execute(
                delete(SessionResponse).where(SessionResponse.session_id == session_id)
            )
            await db.commit()

            for item_id, result in analysis_results.items():
                ai_answer = result["answer"]
                score = 10 if ai_answer else 0

                response = SessionResponse(
                    session_id=session_id,
                    item_id=item_id,
                    ai_answer=ai_answer,
                    ai_reasoning=result["reasoning"],
                    user_answer=None,
                    was_changed=False,
                    score=score,
                )
                db.add(response)
                await db.flush()

                logger.info(
                    "Item %s: %s (%s pts) - %s...",
                    item_id,
                    "YES" if ai_answer else "NO",
                    score,
                    result["reasoning"][:50],
                )

                question_evals = result.get("question_evaluations", [])
                if question_evals:
                    await analyzer.store_question_analyses(
                        session_response_id=response.id,
                        item_id=item_id,
                        question_evaluations=question_evals,
                        db=db,
                        framework=result.get("behavioral_framework"),
                    )
                    logger.info(
                        "  Stored %s question evaluations for item %s",
                        len(question_evals),
                        item_id,
                    )

            session_obj = await db.get(Session, session_id)
            if session_obj:
                session_obj.status = SessionStatus.PENDING_REVIEW

            await db.commit()

        logger.info(
            "Transcription and AI analysis completed for session %s", session_id
        )

    except Exception as e:
        logger.error(
            "Transcription failed for session %s: %s",
            session_id,
            str(e),
            exc_info=True,
        )
        try:
            async with get_db_session() as db:
                session_obj = await db.get(Session, session_id)
                if session_obj:
                    session_obj.status = SessionStatus.FAILED
                await db.commit()
        except Exception as commit_error:
            logger.error(
                "Failed to update session status: %s",
                str(commit_error),
                exc_info=True,
            )
        raise


async def process_transcription(session_id: int, file_path: str) -> None:
    """Entry point for FastAPI BackgroundTasks (async)."""
    await run_transcription_job(session_id, file_path)
