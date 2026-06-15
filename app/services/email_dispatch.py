"""
Queue or send transactional email without blocking the FastAPI event loop.

Stage/prod (USE_CELERY_FOR_EMAIL=true): enqueue Celery tasks on the worker.
Local dev: send inline via asyncio.to_thread (SMTP).
"""
import logging
from typing import List, Optional

from app.core.config import settings
from app.services.email_service import get_email_service

logger = logging.getLogger(__name__)


def _queue_task(task, payload: dict) -> bool:
    task.delay(payload)
    logger.info("Queued %s", task.name)
    return True


async def dispatch_verification_email(
    *, user_email: str, user_name: str, verification_token: str
) -> bool:
    payload = {
        "user_email": user_email,
        "user_name": user_name,
        "verification_token": verification_token,
    }
    if settings.use_celery_for_email:
        from app.tasks.email import send_verification_email_task
        return _queue_task(send_verification_email_task, payload)
    return await get_email_service().send_verification_email_async(**payload)


async def dispatch_password_reset_email(
    *, user_email: str, user_name: str, reset_token: str
) -> bool:
    payload = {
        "user_email": user_email,
        "user_name": user_name,
        "reset_token": reset_token,
    }
    if settings.use_celery_for_email:
        from app.tasks.email import send_password_reset_email_task
        return _queue_task(send_password_reset_email_task, payload)
    return await get_email_service().send_password_reset_email_async(**payload)


async def dispatch_welcome_email(*, user_email: str, user_name: str) -> bool:
    payload = {"user_email": user_email, "user_name": user_name}
    if settings.use_celery_for_email:
        from app.tasks.email import send_welcome_email_task
        return _queue_task(send_welcome_email_task, payload)
    return await get_email_service().send_welcome_email_async(**payload)


async def dispatch_notification_email(
    *,
    to_emails: List[str],
    subject: str,
    message: str,
    user_name: Optional[str] = None,
) -> bool:
    payload = {
        "to_emails": to_emails,
        "subject": subject,
        "message": message,
        "user_name": user_name,
    }
    if settings.use_celery_for_email:
        from app.tasks.email import send_notification_email_task
        return _queue_task(send_notification_email_task, payload)
    return await get_email_service().send_notification_email_async(**payload)


async def dispatch_organization_invitation_email(
    *,
    to_email: str,
    organization_name: str,
    inviter_name: str,
    invite_url: str,
    role: str,
    team_name: Optional[str] = None,
    temp_password: Optional[str] = None,
    is_resend: bool = False,
) -> bool:
    service = get_email_service()
    rendered = service.render_invitation_email(
        to_email=to_email,
        organization_name=organization_name,
        inviter_name=inviter_name,
        invite_url=invite_url,
        role=role,
        team_name=team_name,
        temp_password=temp_password,
        is_resend=is_resend,
    )
    if settings.use_celery_for_email:
        from app.tasks.email import send_invitation_email_task
        return _queue_task(send_invitation_email_task, rendered)
    return await service._send_in_thread(
        service._send_email,
        to_emails=[rendered["to_email"]],
        subject=rendered["subject"],
        html_body=rendered["html_body"],
        text_body=rendered["text_body"],
    )
