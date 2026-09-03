"""SYSTEM_ADMIN endpoints for editing transactional email templates."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_roles
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.email_template import (
    EmailTemplateDetail,
    EmailTemplateListItem,
    EmailTemplatePreviewRequest,
    EmailTemplatePreviewResponse,
    EmailTemplateTestRequest,
    EmailTemplateTestResponse,
    EmailTemplateUpdate,
)
from app.services import email_template_store as store
from app.services.email_service import get_email_service
from app.utils.email_validation import validate_email_address

router = APIRouter()


def _http_for_store_error(exc: Exception) -> HTTPException:
    if isinstance(exc, store.UnknownEmailTemplateError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, store.InvalidEmailTemplateError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


def _detail_from_row(row) -> EmailTemplateDetail:
    meta = store.meta_for(row.slug)
    return EmailTemplateDetail(
        slug=row.slug,
        name=meta["name"],
        description=meta["description"],
        subject=row.subject,
        html_body=row.html_body,
        variables=meta["variables"],
        sample_context=store.build_sample_context(row.slug),
        updated_at=row.updated_at,
        updated_by_user_id=row.updated_by_user_id,
    )


@router.get("/email-templates", response_model=list[EmailTemplateListItem])
async def list_email_templates(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SYSTEM_ADMIN)),
):
    """List platform email templates (SYSTEM_ADMIN only)."""
    rows = await store.list_templates(db)
    items: list[EmailTemplateListItem] = []
    for row in rows:
        meta = store.meta_for(row.slug)
        items.append(
            EmailTemplateListItem(
                slug=row.slug,
                name=meta["name"],
                description=meta["description"],
                updated_at=row.updated_at,
            )
        )
    return items


@router.get("/email-templates/{slug}", response_model=EmailTemplateDetail)
async def get_email_template(
    slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SYSTEM_ADMIN)),
):
    """Get one email template including HTML and available Jinja variables."""
    try:
        row = await store.get_template(db, slug)
    except (store.UnknownEmailTemplateError, store.InvalidEmailTemplateError) as exc:
        raise _http_for_store_error(exc) from exc
    return _detail_from_row(row)


@router.put("/email-templates/{slug}", response_model=EmailTemplateDetail)
async def update_email_template(
    slug: str,
    payload: EmailTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SYSTEM_ADMIN)),
):
    """Save subject and HTML for a template. Changes apply to the next send."""
    try:
        row = await store.save_template(
            db,
            slug,
            subject=payload.subject,
            html_body=payload.html_body,
            updated_by_user_id=current_user.id,
        )
    except (store.UnknownEmailTemplateError, store.InvalidEmailTemplateError) as exc:
        raise _http_for_store_error(exc) from exc
    return _detail_from_row(row)


@router.post("/email-templates/{slug}/preview", response_model=EmailTemplatePreviewResponse)
async def preview_email_template(
    slug: str,
    payload: EmailTemplatePreviewRequest,
    current_user: User = Depends(require_roles(UserRole.SYSTEM_ADMIN)),
):
    """Render a template with sample data (unsaved HTML is allowed)."""
    try:
        rendered = store.preview_template(
            slug,
            subject=payload.subject,
            html_body=payload.html_body,
        )
    except (store.UnknownEmailTemplateError, store.InvalidEmailTemplateError) as exc:
        raise _http_for_store_error(exc) from exc
    return EmailTemplatePreviewResponse(**rendered)


@router.post("/email-templates/{slug}/test", response_model=EmailTemplateTestResponse)
async def test_email_template(
    slug: str,
    payload: EmailTemplateTestRequest,
    current_user: User = Depends(require_roles(UserRole.SYSTEM_ADMIN)),
):
    """Send a sample-data render of this template to an address."""
    try:
        to_email = validate_email_address(payload.to_email)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    try:
        rendered = store.preview_template(slug)
    except (store.UnknownEmailTemplateError, store.InvalidEmailTemplateError) as exc:
        raise _http_for_store_error(exc) from exc

    email_service = get_email_service()
    sent = await email_service._send_in_thread(
        email_service._send_email,
        to_emails=[to_email],
        subject=f"[TEST] {rendered['subject']}",
        html_body=rendered["html_body"],
    )
    if not sent:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The test email could not be sent. Check email provider configuration.",
        )
    return EmailTemplateTestResponse(
        sent=True,
        to_email=to_email,
        subject=f"[TEST] {rendered['subject']}",
    )


@router.post("/email-templates/{slug}/reset", response_model=EmailTemplateDetail)
async def reset_email_template(
    slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SYSTEM_ADMIN)),
):
    """Restore the code default subject and HTML for this template."""
    try:
        row = await store.reset_template(
            db,
            slug,
            updated_by_user_id=current_user.id,
        )
    except (store.UnknownEmailTemplateError, store.InvalidEmailTemplateError) as exc:
        raise _http_for_store_error(exc) from exc
    return _detail_from_row(row)
