"""
Queue or send transactional email without blocking the FastAPI event loop.

Stage/prod (USE_CELERY_FOR_EMAIL=true): enqueue Celery tasks on the worker.
The worker container MUST have the same SES env as the API (SES_SENDER_EMAIL,
SES_REGION). Local dev: send inline via SMTP on the API process.
"""
import logging
from typing import Awaitable, Callable, List, Optional

from app.core.config import settings
from app.services.email_service import get_email_service

logger = logging.getLogger(__name__)


def _queue_task(task, payload: dict, *, recipients: str) -> bool:
    """Enqueue on Celery. Returns False if the broker rejects the task."""
    try:
        task.delay(payload)
        logger.info("Queued %s for %s", task.name, recipients)
        return True
    except Exception:
        logger.exception(
            "Failed to queue %s for %s — will try inline send on API",
            task.name,
            recipients,
        )
        return False


async def _dispatch(
    *,
    task,
    payload: dict,
    recipients: str,
    inline_send: Callable[[], Awaitable[bool]],
) -> bool:
    """Queue on worker when configured; fall back to inline API send on failure."""
    if settings.use_celery_for_email:
        if _queue_task(task, payload, recipients=recipients):
            return True
        logger.warning(
            "Celery unavailable for %s — sending inline from API (has SES env)",
            recipients,
        )
    return await inline_send()


async def dispatch_verification_email(
    *, user_email: str, user_name: str, verification_token: str
) -> bool:
    payload = {
        "user_email": user_email,
        "user_name": user_name,
        "verification_token": verification_token,
    }
    from app.tasks.email import send_verification_email_task

    return await _dispatch(
        task=send_verification_email_task,
        payload=payload,
        recipients=user_email,
        inline_send=lambda: get_email_service().send_verification_email_async(
            **payload
        ),
    )


async def dispatch_password_reset_email(
    *, user_email: str, user_name: str, reset_token: str
) -> bool:
    payload = {
        "user_email": user_email,
        "user_name": user_name,
        "reset_token": reset_token,
    }
    from app.tasks.email import send_password_reset_email_task

    return await _dispatch(
        task=send_password_reset_email_task,
        payload=payload,
        recipients=user_email,
        inline_send=lambda: get_email_service().send_password_reset_email_async(
            **payload
        ),
    )


async def dispatch_welcome_email(*, user_email: str, user_name: str) -> bool:
    payload = {"user_email": user_email, "user_name": user_name}
    from app.tasks.email import send_welcome_email_task

    return await _dispatch(
        task=send_welcome_email_task,
        payload=payload,
        recipients=user_email,
        inline_send=lambda: get_email_service().send_welcome_email_async(**payload),
    )


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
    from app.tasks.email import send_notification_email_task

    return await _dispatch(
        task=send_notification_email_task,
        payload=payload,
        recipients=",".join(to_emails),
        inline_send=lambda: get_email_service().send_notification_email_async(
            **payload
        ),
    )


async def dispatch_registration_approved_email(
    *,
    to_email: str,
    user_name: str,
    organization_name: str,
    approver_name: str,
    temp_password: str,
    sign_in_url: str,
) -> bool:
    service = get_email_service()
    rendered = service.render_registration_approved_email(
        to_email=to_email,
        user_name=user_name,
        organization_name=organization_name,
        approver_name=approver_name,
        temp_password=temp_password,
        sign_in_url=sign_in_url,
    )
    from app.tasks.email import send_registration_approved_email_task

    return await _dispatch(
        task=send_registration_approved_email_task,
        payload=rendered,
        recipients=to_email,
        inline_send=lambda: service.send_registration_approved_email_async(rendered),
    )


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
    from app.tasks.email import send_invitation_email_task

    async def inline_send() -> bool:
        return await service._send_in_thread(
            service._send_email,
            to_emails=[rendered["to_email"]],
            subject=rendered["subject"],
            html_body=rendered["html_body"],
            text_body=rendered["text_body"],
        )

    return await _dispatch(
        task=send_invitation_email_task,
        payload=rendered,
        recipients=to_email,
        inline_send=inline_send,
    )


async def dispatch_manager_note_email(
    *,
    rep_email: str,
    rep_name: str,
    manager_name: str,
    customer_name: str,
    opportunity_name: str,
    session_id: int,
    note_type: str,
    note_text: Optional[str] = None,
) -> bool:
    """Notify the session rep that a manager left coaching feedback."""
    import html

    service = get_email_service()
    session_url = f"{settings.FRONTEND_URL.rstrip('/')}/session/{session_id}/results"
    note_preview = None
    if note_type == "text" and note_text:
        trimmed = note_text.strip()
        if len(trimmed) > 200:
            trimmed = f"{trimmed[:200].rstrip()}..."
        note_preview = html.escape(trimmed)

    rendered = service.render_manager_note_email(
        rep_email=rep_email,
        rep_name=rep_name,
        manager_name=manager_name,
        customer_name=customer_name,
        opportunity_name=opportunity_name,
        session_url=session_url,
        note_type=note_type,
        note_preview=note_preview,
    )
    from app.tasks.email import send_manager_note_email_task

    async def inline_send() -> bool:
        return await service.send_manager_note_email_async(rendered)

    return await _dispatch(
        task=send_manager_note_email_task,
        payload=rendered,
        recipients=rep_email,
        inline_send=inline_send,
    )
