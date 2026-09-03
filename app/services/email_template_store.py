"""
Load, seed, save, and render Super Admin email templates.

Code defaults in email_templates.py remain the reset source. Saved HTML lives
in Postgres so edits apply without a deploy. Celery workers use a sync session.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

from jinja2 import TemplateSyntaxError
from jinja2.sandbox import SandboxedEnvironment
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import SyncSessionLocal
from app.models.email_template import EmailTemplate
from app.services.email_templates import (
    EMAIL_TEMPLATE_META,
    get_default_html,
    get_default_subject,
    get_template_variables,
    list_template_slugs,
)

logger = logging.getLogger(__name__)

SUBJECT_MAX_LENGTH = 500
HTML_MAX_LENGTH = 500_000

_jinja_env = SandboxedEnvironment()


class UnknownEmailTemplateError(ValueError):
    pass


class InvalidEmailTemplateError(ValueError):
    pass


def require_known_slug(slug: str) -> str:
    if slug not in set(list_template_slugs()):
        raise UnknownEmailTemplateError(f"Unknown email template: {slug}")
    return slug


def jinja_env() -> SandboxedEnvironment:
    return _jinja_env


def validate_jinja(subject: str, html_body: str) -> None:
    if not subject or not subject.strip():
        raise InvalidEmailTemplateError("Subject is required")
    if len(subject) > SUBJECT_MAX_LENGTH:
        raise InvalidEmailTemplateError(
            f"Subject must be {SUBJECT_MAX_LENGTH} characters or fewer"
        )
    if not html_body or not html_body.strip():
        raise InvalidEmailTemplateError("HTML body is required")
    if len(html_body) > HTML_MAX_LENGTH:
        raise InvalidEmailTemplateError(
            f"HTML body must be {HTML_MAX_LENGTH} characters or fewer"
        )
    try:
        _jinja_env.from_string(subject)
        _jinja_env.from_string(html_body)
    except TemplateSyntaxError as exc:
        raise InvalidEmailTemplateError(f"Invalid Jinja syntax: {exc}") from exc


def _frontend_url() -> str:
    return (settings.FRONTEND_URL or "http://localhost:3000").rstrip("/")


def build_sample_context(slug: str) -> dict[str, Any]:
    """Placeholder values for preview and test-send. Never real tokens or passwords."""
    base_url = _frontend_url()
    common = {
        "project_name": settings.PROJECT_NAME,
        "company_name": settings.EMAIL_COMPANY_NAME,
        "current_year": datetime.utcnow().year,
    }
    extras: dict[str, dict[str, Any]] = {
        "email_verification": {
            "user_name": "Alex Rivera",
            "user_email": "alex.rivera@example.com",
            "verification_url": f"{base_url}/verify-email?token=sample-preview-token",
        },
        "password_reset": {
            "user_name": "Alex Rivera",
            "user_email": "alex.rivera@example.com",
            "reset_url": f"{base_url}/reset-password?token=sample-preview-token",
        },
        "welcome": {
            "user_name": "Alex Rivera",
            "user_email": "alex.rivera@example.com",
            "dashboard_url": f"{base_url}/dashboard",
        },
        "registration_approved": {
            "user_name": "Alex Rivera",
            "user_email": "alex.rivera@example.com",
            "organization_name": "Acme Sales",
            "approver_name": "Dana Park",
            "temp_password": "SamplePass123",
            "sign_in_url": f"{base_url}/login",
        },
        "invitation": {
            "user_email": "alex.rivera@example.com",
            "organization_name": "Acme Sales",
            "inviter_name": "Dana Park",
            "invite_url": f"{base_url}/accept-invite?token=sample-preview-token",
            "role": "rep",
            "team_name": "Enterprise West",
            "temp_password": "SamplePass123",
            "is_resend": False,
        },
        "manager_note": {
            "rep_email": "alex.rivera@example.com",
            "rep_name": "Alex Rivera",
            "manager_name": "Dana Park",
            "customer_name": "Northwind Manufacturing",
            "opportunity_name": "Q3 expansion",
            "session_url": f"{base_url}/session/0/results",
            "note_type": "text",
            "note_preview": "Great discovery on budget authority — follow up on the timeline next call.",
        },
        "notification": {
            "subject": "Sample notification",
            "greeting": "Hello Alex Rivera,",
            "message": (
                "Thank you for registering <strong>Acme Sales</strong>. "
                "This is a sample notification used for preview and test sends."
            ),
            "user_name": "Alex Rivera",
            "user_email": "alex.rivera@example.com",
        },
    }
    return {**common, **extras.get(slug, {})}


def render_strings(subject_src: str, html_src: str, context: dict[str, Any]) -> dict[str, str]:
    subject = _jinja_env.from_string(subject_src).render(**context).strip()
    html_body = _jinja_env.from_string(html_src).render(**context)
    return {"subject": subject, "html_body": html_body}


def get_sources_sync(slug: str) -> tuple[str, str]:
    """Return (subject, html_body) from DB or code default. Safe for Celery workers."""
    require_known_slug(slug)
    try:
        with SyncSessionLocal() as session:
            row = session.get(EmailTemplate, slug)
            if row and row.subject and row.html_body:
                return row.subject, row.html_body
    except Exception:
        logger.exception("Failed to load email template %s from database; using code default", slug)
    return get_default_subject(slug), get_default_html(slug)


def meta_for(slug: str) -> dict[str, Any]:
    require_known_slug(slug)
    info = EMAIL_TEMPLATE_META.get(slug, {})
    return {
        "slug": slug,
        "name": info.get("name") or slug.replace("_", " ").title(),
        "description": info.get("description") or "",
        "variables": get_template_variables(slug),
    }


def _new_row(slug: str) -> EmailTemplate:
    info = meta_for(slug)
    return EmailTemplate(
        slug=slug,
        name=info["name"],
        description=info["description"],
        subject=get_default_subject(slug),
        html_body=get_default_html(slug),
    )


async def ensure_seeded(db: AsyncSession) -> None:
    """Insert any registry templates that are missing from the database."""
    result = await db.execute(select(EmailTemplate.slug))
    existing = set(result.scalars().all())
    created = False
    for slug in list_template_slugs():
        if slug not in existing:
            db.add(_new_row(slug))
            created = True
    if created:
        await db.flush()


async def list_templates(db: AsyncSession) -> list[EmailTemplate]:
    await ensure_seeded(db)
    result = await db.execute(select(EmailTemplate))
    rows = {row.slug: row for row in result.scalars().all()}
    return [rows[slug] for slug in list_template_slugs() if slug in rows]


async def get_template(db: AsyncSession, slug: str) -> EmailTemplate:
    require_known_slug(slug)
    await ensure_seeded(db)
    row = await db.get(EmailTemplate, slug)
    if row is None:
        row = _new_row(slug)
        db.add(row)
        await db.flush()
    return row


async def save_template(
    db: AsyncSession,
    slug: str,
    *,
    subject: str,
    html_body: str,
    updated_by_user_id: Optional[int],
) -> EmailTemplate:
    require_known_slug(slug)
    validate_jinja(subject, html_body)
    row = await get_template(db, slug)
    info = meta_for(slug)
    row.name = info["name"]
    row.description = info["description"]
    row.subject = subject
    row.html_body = html_body
    row.updated_by_user_id = updated_by_user_id
    await db.flush()
    await db.refresh(row)
    return row


async def reset_template(
    db: AsyncSession,
    slug: str,
    *,
    updated_by_user_id: Optional[int],
) -> EmailTemplate:
    require_known_slug(slug)
    row = await get_template(db, slug)
    info = meta_for(slug)
    row.name = info["name"]
    row.description = info["description"]
    row.subject = get_default_subject(slug)
    row.html_body = get_default_html(slug)
    row.updated_by_user_id = updated_by_user_id
    await db.flush()
    await db.refresh(row)
    return row


def preview_template(
    slug: str,
    *,
    subject: Optional[str] = None,
    html_body: Optional[str] = None,
) -> dict[str, str]:
    require_known_slug(slug)
    stored_subject, stored_html = get_sources_sync(slug)
    subject_src = stored_subject if subject is None else subject
    html_src = stored_html if html_body is None else html_body
    validate_jinja(subject_src, html_src)
    return render_strings(subject_src, html_src, build_sample_context(slug))
