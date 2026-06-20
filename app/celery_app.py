"""
Celery application for background jobs (transcription, etc.).

Run worker:
  celery -A app.celery_app worker --loglevel=info
"""
from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "sales_checklist",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.transcription", "app.tasks.email", "app.tasks.knowledge_base"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,
    task_soft_time_limit=3300,
    worker_prefetch_multiplier=1,
)


@celery_app.on_after_configure.connect
def _log_worker_email_config(sender, **kwargs) -> None:
    """Warn loudly if the worker cannot send SES email (common misconfiguration)."""
    import logging

    log = logging.getLogger(__name__)
    if settings.email_provider == "ses" and not (settings.SES_SENDER_EMAIL or "").strip():
        log.critical(
            "Celery worker missing SES_SENDER_EMAIL — all email tasks will fail. "
            "Add SES_SENDER_EMAIL and SES_REGION to the worker task definition."
        )
