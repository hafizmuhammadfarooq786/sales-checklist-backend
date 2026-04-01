"""
Celery tasks for audio transcription pipeline.
"""
import asyncio
import logging

from app.celery_app import celery_app
from app.services.transcription_pipeline import run_transcription_job

logger = logging.getLogger(__name__)


@celery_app.task(name="transcription.process_session", bind=True, max_retries=0)
def process_transcription_task(self, session_id: int, file_path: str) -> None:
    """
    Runs the async transcription pipeline in a dedicated worker process.
    Retries are disabled; failures mark the session failed inside the pipeline.
    """
    logger.info("Celery: starting transcription for session %s", session_id)
    asyncio.run(run_transcription_job(session_id, file_path))
    logger.info("Celery: finished transcription for session %s", session_id)
