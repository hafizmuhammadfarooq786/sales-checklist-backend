"""
Schedule transcription jobs: Celery worker (production) or FastAPI BackgroundTasks (fallback).
"""
import logging
from typing import Optional

from fastapi import BackgroundTasks

from app.core.config import settings
from app.services.transcription_pipeline import process_transcription

logger = logging.getLogger(__name__)


def schedule_transcription(
    session_id: int,
    file_path: str,
    background_tasks: Optional[BackgroundTasks],
) -> str:
    """
    Returns ``\"celery\"`` if the task was queued on the broker, else ``\"background\"``.
    """
    if settings.USE_CELERY_FOR_TRANSCRIPTION:
        try:
            from app.tasks.transcription import process_transcription_task

            process_transcription_task.delay(session_id, file_path)
            logger.info(
                "Transcription queued (Celery) for session %s", session_id
            )
            return "celery"
        except Exception as e:
            logger.warning(
                "Celery enqueue failed for session %s, using BackgroundTasks: %s",
                session_id,
                e,
            )

    if background_tasks is None:
        raise ValueError(
            "background_tasks is required when Celery is disabled or unavailable"
        )
    background_tasks.add_task(process_transcription, session_id, file_path)
    logger.info(
        "Transcription scheduled (BackgroundTasks) for session %s", session_id
    )
    return "background"
