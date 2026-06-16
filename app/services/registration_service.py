"""Public organization registration submit + Super Admin approval orchestration."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import Organization, OrganizationSettings, User
from app.models.organization_registration import (
    OrganizationRegistrationRequest,
    RegistrationStatus,
)
from app.models.user import UserRole
from app.schemas.organization_registration import OrganizationRegistrationCreate
from app.services.auth_service import auth_service
from app.services.email_dispatch import (
    dispatch_notification_email,
    dispatch_registration_approved_email,
)
from app.services.invitation_service import get_invitation_service
from app.services.s3_service import get_s3_service

logger = logging.getLogger(__name__)

_LOGO_MAX_BYTES = 2 * 1024 * 1024
_LOGO_ALLOWED_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


class OrganizationRegistrationService:
    async def submit_registration(
        self,
        db: AsyncSession,
        payload: OrganizationRegistrationCreate,
        logo_bytes: Optional[bytes] = None,
        logo_content_type: Optional[str] = None,
    ) -> OrganizationRegistrationRequest:
        admin_email = payload.admin_email.strip().lower()
        await self._ensure_signup_allowed(db, admin_email, payload.company_name)

        request = OrganizationRegistrationRequest(
            status=RegistrationStatus.PENDING,
            company_name=payload.company_name.strip(),
            industry=payload.industry.strip(),
            admin_first_name=payload.admin_first_name.strip(),
            admin_last_name=payload.admin_last_name.strip(),
            admin_email=admin_email,
            admin_direct_dial=payload.admin_direct_dial.strip(),
            admin_cell_phone=(payload.admin_cell_phone or "").strip() or None,
            additional_users=[user.model_dump(mode="json") for user in payload.additional_users],
        )
        db.add(request)
        await db.flush()

        if logo_bytes:
            request.logo_url = await self._store_pending_logo(
                request.id,
                logo_bytes,
                logo_content_type or "image/png",
            )

        await db.commit()
        await db.refresh(request)

        await dispatch_notification_email(
            to_emails=[admin_email],
            subject=f"We received your {settings.PROJECT_NAME} registration",
            message=(
                f"Thank you for registering <strong>{request.company_name}</strong>. "
                "Our team is reviewing your application and will email you when it is approved."
            ),
            user_name=f"{request.admin_first_name} {request.admin_last_name}".strip(),
        )
        await self._notify_system_admins(db, request)
        return request

    async def approve_registration(
        self,
        db: AsyncSession,
        request_id: int,
        reviewer: User,
        frontend_url: Optional[str] = None,
    ) -> tuple[OrganizationRegistrationRequest, int, int]:
        request = await self._get_request(db, request_id)
        if request.status != RegistrationStatus.PENDING:
            raise ValueError("Registration request is not pending")

        admin_email = request.admin_email.strip().lower()
        await self._ensure_signup_allowed(db, admin_email, request.company_name, exclude_request_id=request.id)

        existing_org = await db.execute(
            select(Organization).where(Organization.name == request.company_name)
        )
        if existing_org.scalar_one_or_none():
            raise ValueError(f"Organization '{request.company_name}' already exists")

        organization = Organization(
            name=request.company_name,
            industry=request.industry,
            is_active=True,
        )
        db.add(organization)
        await db.flush()

        logo_url = await self._finalize_logo_for_org(request.logo_url, organization.id)
        org_settings = OrganizationSettings(
            organization_id=organization.id,
            allow_self_registration=False,
            default_role="rep",
            logo_url=logo_url,
            settings={},
        )
        db.add(org_settings)
        await db.flush()

        invitation_service = get_invitation_service()
        base_url = (frontend_url or settings.FRONTEND_URL).rstrip("/")
        reviewer_name = f"{reviewer.first_name or ''} {reviewer.last_name or ''}".strip() or reviewer.email
        admin_name = f"{request.admin_first_name} {request.admin_last_name}".strip()

        temp_password = invitation_service.generate_temp_password()
        admin_user = User(
            email=admin_email,
            password_hash=auth_service.hash_password(temp_password),
            first_name=request.admin_first_name.strip(),
            last_name=request.admin_last_name.strip(),
            job_title=getattr(request, "admin_job_title", None) or "Executive Sponsor",
            direct_dial=request.admin_direct_dial,
            cell_phone=request.admin_cell_phone,
            organization_id=organization.id,
            role=UserRole.ADMIN,
            is_active=True,
            must_change_password=True,
        )
        db.add(admin_user)
        await db.flush()

        email_sent = await dispatch_registration_approved_email(
            to_email=admin_email,
            user_name=admin_name or admin_email,
            organization_name=request.company_name,
            approver_name=reviewer_name,
            temp_password=temp_password,
            sign_in_url=f"{base_url}/sign-in",
        )
        if not email_sent:
            raise ValueError(f"Failed to send approval email to {admin_email}")

        invitations_sent = 0
        for row in request.additional_users or []:
            role = str(row["role"]).lower()
            if role not in {"rep", "manager"}:
                raise ValueError(
                    f"Invalid role for additional user {row.get('email')}: only manager or rep allowed"
                )
            await invitation_service.create_invitation(
                db=db,
                email=str(row["email"]).strip().lower(),
                organization_id=organization.id,
                role=role,
                invited_by=admin_user.id,
                frontend_url=base_url,
                first_name=str(row.get("first_name") or "").strip() or None,
                last_name=str(row.get("last_name") or "").strip() or None,
                job_title=str(row.get("job_title") or row.get("title") or "").strip() or None,
                direct_dial=str(row.get("direct_dial") or "").strip() or None,
                cell_phone=str(row.get("cell_phone") or "").strip() or None,
                auto_commit=False,
            )
            invitations_sent += 1

        request.status = RegistrationStatus.APPROVED
        request.organization_id = organization.id
        request.reviewed_by = reviewer.id
        request.reviewed_at = datetime.utcnow()
        request.rejection_reason = None

        await db.commit()
        await db.refresh(request)
        return request, organization.id, invitations_sent

    async def reject_registration(
        self,
        db: AsyncSession,
        request_id: int,
        reviewer: User,
        reason: Optional[str] = None,
    ) -> OrganizationRegistrationRequest:
        request = await self._get_request(db, request_id)
        if request.status != RegistrationStatus.PENDING:
            raise ValueError("Registration request is not pending")

        request.status = RegistrationStatus.REJECTED
        request.reviewed_by = reviewer.id
        request.reviewed_at = datetime.utcnow()
        request.rejection_reason = (reason or "").strip() or None
        await db.commit()
        await db.refresh(request)

        message = (
            f"Your registration for <strong>{request.company_name}</strong> was not approved."
        )
        if request.rejection_reason:
            message += f"<br><br>Reason: {request.rejection_reason}"

        await dispatch_notification_email(
            to_emails=[request.admin_email],
            subject="Your organization registration update",
            message=message,
            user_name=f"{request.admin_first_name} {request.admin_last_name}".strip(),
        )
        return request

    async def _get_request(
        self,
        db: AsyncSession,
        request_id: int,
    ) -> OrganizationRegistrationRequest:
        result = await db.execute(
            select(OrganizationRegistrationRequest).where(
                OrganizationRegistrationRequest.id == request_id
            )
        )
        request = result.scalar_one_or_none()
        if not request:
            raise ValueError("Registration request not found")
        return request

    async def _ensure_signup_allowed(
        self,
        db: AsyncSession,
        admin_email: str,
        company_name: str,
        exclude_request_id: Optional[int] = None,
    ) -> None:
        user_result = await db.execute(
            select(User).where(User.email == admin_email, User.deleted_at.is_(None))
        )
        if user_result.scalar_one_or_none():
            raise ValueError("An account with this administrator email already exists")

        pending_query = select(OrganizationRegistrationRequest).where(
            OrganizationRegistrationRequest.status == RegistrationStatus.PENDING,
            OrganizationRegistrationRequest.admin_email == admin_email,
        )
        if exclude_request_id:
            pending_query = pending_query.where(
                OrganizationRegistrationRequest.id != exclude_request_id
            )
        pending = await db.execute(pending_query)
        if pending.scalar_one_or_none():
            raise ValueError("A pending registration already exists for this email")

        org_result = await db.execute(
            select(Organization).where(Organization.name == company_name.strip())
        )
        if org_result.scalar_one_or_none():
            raise ValueError(f"Organization '{company_name.strip()}' already exists")

    async def _store_pending_logo(
        self,
        request_id: int,
        file_bytes: bytes,
        content_type: str,
    ) -> str:
        ext = _LOGO_ALLOWED_TYPES.get(content_type.lower(), ".png")
        s3_key = f"pending-registrations/{request_id}/logo-{uuid.uuid4().hex}{ext}"
        try:
            s3_service = get_s3_service()
            return await s3_service.upload_bytes(file_bytes, s3_key, content_type=content_type)
        except Exception:
            logo_url = f"uploads/pending-registrations/{request_id}/logo{ext}"
            local_path = Path(logo_url)
            local_path.parent.mkdir(parents=True, exist_ok=True)
            local_path.write_bytes(file_bytes)
            return logo_url

    async def _finalize_logo_for_org(
        self,
        logo_url: Optional[str],
        organization_id: int,
    ) -> Optional[str]:
        if not logo_url:
            return None

        source = logo_url.strip()
        if source.startswith("branding/"):
            return source

        ext = Path(source.split("?")[0]).suffix or ".png"
        if not ext.startswith("."):
            ext = f".{ext}"

        try:
            from app.services.org_logo_service import load_organization_logo_bytes

            logo_bytes = await load_organization_logo_bytes(source)
            if not logo_bytes:
                return source

            dest_key = f"branding/{organization_id}/logo-{uuid.uuid4().hex}{ext}"
            s3_service = get_s3_service()
            content_type = {
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".webp": "image/webp",
                ".gif": "image/gif",
            }.get(ext.lower(), "image/png")
            return await s3_service.upload_bytes(logo_bytes, dest_key, content_type=content_type)
        except Exception:
            dest = Path(f"uploads/branding/{organization_id}/logo{ext}")
            src_path = Path(source)
            if src_path.is_file():
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(src_path.read_bytes())
                return str(dest)
            return source

    async def _notify_system_admins(
        self,
        db: AsyncSession,
        request: OrganizationRegistrationRequest,
    ) -> None:
        admins_result = await db.execute(
            select(User).where(
                User.role == UserRole.SYSTEM_ADMIN,
                User.is_active.is_(True),
                User.deleted_at.is_(None),
            )
        )
        admins = admins_result.scalars().all()
        if not admins:
            return

        review_url = f"{settings.FRONTEND_URL.rstrip('/')}/admin/registrations"
        for admin in admins:
            if not admin.email:
                continue
            await dispatch_notification_email(
                to_emails=[admin.email],
                subject=f"New organization registration: {request.company_name}",
                message=(
                    f"<strong>{request.company_name}</strong> submitted a new registration "
                    f"request (administrator: {request.admin_email}). "
                    f'Review it in the admin queue: <a href="{review_url}">{review_url}</a>'
                ),
                user_name=f"{admin.first_name or ''} {admin.last_name or ''}".strip() or None,
            )


registration_service = OrganizationRegistrationService()


def get_registration_service() -> OrganizationRegistrationService:
    return registration_service
