"""
Celery tasks for transactional email (SMTP local, SES stage/prod).

Workers call the synchronous EmailService methods — blocking I/O is fine in a
dedicated worker process and does not block the FastAPI event loop.
"""
import logging
from typing import Any, Dict

from app.celery_app import celery_app
from app.services.email_service import get_email_service

logger = logging.getLogger(__name__)


@celery_app.task(name="email.send_verification", bind=True, max_retries=3, default_retry_delay=60)
def send_verification_email_task(self, payload: Dict[str, Any]) -> bool:
    try:
        ok = get_email_service().send_verification_email(**payload)
        if not ok:
            raise RuntimeError(f"Verification email not sent to {payload.get('user_email')}")
        return ok
    except Exception as exc:
        logger.exception("Verification email task failed")
        raise self.retry(exc=exc)


@celery_app.task(name="email.send_password_reset", bind=True, max_retries=3, default_retry_delay=60)
def send_password_reset_email_task(self, payload: Dict[str, Any]) -> bool:
    try:
        ok = get_email_service().send_password_reset_email(**payload)
        if not ok:
            raise RuntimeError(f"Password reset email not sent to {payload.get('user_email')}")
        return ok
    except Exception as exc:
        logger.exception("Password reset email task failed")
        raise self.retry(exc=exc)


@celery_app.task(name="email.send_welcome", bind=True, max_retries=3, default_retry_delay=60)
def send_welcome_email_task(self, payload: Dict[str, Any]) -> bool:
    try:
        ok = get_email_service().send_welcome_email(**payload)
        if not ok:
            raise RuntimeError(f"Welcome email not sent to {payload.get('user_email')}")
        return ok
    except Exception as exc:
        logger.exception("Welcome email task failed")
        raise self.retry(exc=exc)


@celery_app.task(name="email.send_notification", bind=True, max_retries=3, default_retry_delay=60)
def send_notification_email_task(self, payload: Dict[str, Any]) -> bool:
    try:
        ok = get_email_service().send_notification_email(**payload)
        if not ok:
            recipients = payload.get("to_emails", [])
            raise RuntimeError(f"Notification email not sent to {recipients}")
        return ok
    except Exception as exc:
        logger.exception("Notification email task failed")
        raise self.retry(exc=exc)


@celery_app.task(name="email.send_invitation", bind=True, max_retries=3, default_retry_delay=60)
def send_invitation_email_task(self, payload: Dict[str, Any]) -> bool:
    try:
        service = get_email_service()
        ok = service._send_email(
            to_emails=[payload["to_email"]],
            subject=payload["subject"],
            html_body=payload["html_body"],
            text_body=payload.get("text_body"),
        )
        if not ok:
            raise RuntimeError(f"Invitation email not sent to {payload.get('to_email')}")
        return ok
    except Exception as exc:
        logger.exception("Invitation email task failed")
        raise self.retry(exc=exc)


@celery_app.task(name="email.send_manager_note", bind=True, max_retries=3, default_retry_delay=60)
def send_manager_note_email_task(self, payload: Dict[str, Any]) -> bool:
    try:
        service = get_email_service()
        ok = service._send_email(
            to_emails=[payload["to_email"]],
            subject=payload["subject"],
            html_body=payload["html_body"],
            text_body=payload.get("text_body"),
        )
        if not ok:
            raise RuntimeError(f"Manager note email not sent to {payload.get('to_email')}")
        return ok
    except Exception as exc:
        logger.exception("Manager note email task failed")
        raise self.retry(exc=exc)
