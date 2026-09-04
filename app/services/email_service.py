"""
Amazon SES Email Service
"""

import asyncio
import boto3
import logging
import smtplib
import ssl
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Optional, Dict, Any
from botocore.exceptions import ClientError, BotoCoreError
from markupsafe import Markup
from app.core.config import settings
from app.services.email_template_store import get_sources_sync, render_strings

logger = logging.getLogger(__name__)


class EmailService:
    """Transactional email service (SMTP for local dev, SES for stage/prod)."""

    def __init__(self):
        self.ses_client = None
        provider = settings.email_provider
        logger.info("Email provider: %s (ENVIRONMENT=%s)", provider, settings.ENVIRONMENT)

        if provider == "ses":
            self.ses_client = self._build_ses_client()
            if not self.ses_client:
                logger.error(
                    "SES provider selected but SES client failed to initialize. "
                    "Set SES_SENDER_EMAIL and ensure AWS credentials or ECS task role."
                )
            elif not settings.SES_SENDER_EMAIL:
                logger.error(
                    "SES provider selected but SES_SENDER_EMAIL is not configured."
                )
        elif not settings.SMTP_HOST or not settings.SMTP_SENDER_EMAIL:
            logger.warning(
                "SMTP provider selected but SMTP_HOST/SMTP_SENDER_EMAIL missing."
            )

    @staticmethod
    def _build_ses_client():
        """Create SES client using explicit keys or the default AWS credential chain."""
        try:
            kwargs: Dict[str, Any] = {"region_name": settings.SES_REGION}
            if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
                kwargs["aws_access_key_id"] = settings.AWS_ACCESS_KEY_ID
                kwargs["aws_secret_access_key"] = settings.AWS_SECRET_ACCESS_KEY
            client = boto3.client("ses", **kwargs)
            logger.info("SES client initialized for region: %s", settings.SES_REGION)
            return client
        except Exception as exc:
            logger.error("Failed to initialize SES client: %s", exc)
            return None

    @staticmethod
    def _template_context(**extra: Any) -> Dict[str, Any]:
        return {
            "project_name": settings.PROJECT_NAME,
            "company_name": settings.EMAIL_COMPANY_NAME,
            "current_year": datetime.utcnow().year,
            **extra,
        }

    def _render_slug(self, slug: str, **extra: Any) -> Dict[str, str]:
        """Render stored (or default) subject + HTML for a named template."""
        subject_src, html_src = get_sources_sync(slug)
        return render_strings(subject_src, html_src, self._template_context(**extra))

    def _send_email(
        self,
        to_emails: List[str],
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
        reply_to: Optional[str] = None,
    ) -> bool:
        """Send email using the configured provider (no cross-provider fallback)."""
        provider = settings.email_provider
        if provider == "ses":
            return self._send_email_via_ses(
                to_emails=to_emails,
                subject=subject,
                html_body=html_body,
                text_body=text_body,
                reply_to=reply_to,
            )
        if provider == "smtp":
            return self._send_email_via_smtp(
                to_emails=to_emails,
                subject=subject,
                html_body=html_body,
                text_body=text_body,
                reply_to=reply_to,
            )
        logger.error("Unknown EMAIL_PROVIDER: %s", provider)
        return False

    async def _send_in_thread(self, send_fn, *args, **kwargs) -> bool:
        """Run blocking SMTP/SES I/O in a thread pool from async endpoints."""
        return await asyncio.to_thread(send_fn, *args, **kwargs)

    async def send_verification_email_async(self, **kwargs) -> bool:
        return await self._send_in_thread(self.send_verification_email, **kwargs)

    async def send_password_reset_email_async(self, **kwargs) -> bool:
        return await self._send_in_thread(self.send_password_reset_email, **kwargs)

    async def send_welcome_email_async(self, **kwargs) -> bool:
        return await self._send_in_thread(self.send_welcome_email, **kwargs)

    async def send_notification_email_async(self, **kwargs) -> bool:
        return await self._send_in_thread(self.send_notification_email, **kwargs)

    def _send_email_via_ses(
        self,
        to_emails: List[str],
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
        reply_to: Optional[str] = None,
    ) -> bool:
        if not self.ses_client or not settings.SES_SENDER_EMAIL:
            logger.error(
                "Cannot send via SES: client or SES_SENDER_EMAIL not configured."
            )
            return False

        try:
            message = {
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {"Html": {"Data": html_body, "Charset": "UTF-8"}},
            }
            if text_body:
                message["Body"]["Text"] = {"Data": text_body, "Charset": "UTF-8"}

            response = self.ses_client.send_email(
                Source=settings.SES_SENDER_EMAIL,
                Destination={"ToAddresses": to_emails},
                Message=message,
                ReplyToAddresses=[reply_to] if reply_to else [],
            )
            message_id = response.get("MessageId")
            logger.info(
                "Email sent via SES to %s (MessageId: %s)", to_emails, message_id
            )
            return True
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code")
            error_message = exc.response.get("Error", {}).get("Message")
            logger.error(
                "AWS SES ClientError [%s]: %s", error_code, error_message
            )
            return False
        except BotoCoreError as exc:
            logger.error("AWS SES BotoCoreError: %s", exc)
            return False
        except Exception as exc:
            logger.error("Unexpected SES error: %s", exc)
            return False

    def _send_email_via_smtp(
        self,
        to_emails: List[str],
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
        reply_to: Optional[str] = None,
    ) -> bool:
        """
        Send an email using SMTP (local development only).
        - SMTP_HOST
        - SMTP_PORT
        - SMTP_USERNAME (optional)
        - SMTP_PASSWORD (optional)
        - SMTP_SENDER_EMAIL
        """
        if not settings.SMTP_HOST or not settings.SMTP_SENDER_EMAIL:
            logger.error(
                "SMTP not configured (SMTP_HOST/SMTP_SENDER_EMAIL missing). Cannot send email."
            )
            return False

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = str(subject)
            msg["From"] = settings.SMTP_SENDER_EMAIL
            msg["To"] = ", ".join(to_emails)
            if reply_to:
                msg["Reply-To"] = reply_to

            if text_body:
                msg.attach(MIMEText(text_body, "plain", "utf-8"))
            else:
                # Some SMTP providers behave better if Text part exists.
                msg.attach(MIMEText("", "plain", "utf-8"))
            msg.attach(MIMEText(html_body, "html", "utf-8"))

            timeout = getattr(settings, "SMTP_TIMEOUT_SECONDS", 30)
            if settings.SMTP_USE_SSL:
                server = smtplib.SMTP_SSL(
                    settings.SMTP_HOST, settings.SMTP_PORT, timeout=timeout
                )
            else:
                server = smtplib.SMTP(
                    settings.SMTP_HOST, settings.SMTP_PORT, timeout=timeout
                )
                if settings.SMTP_USE_TLS:
                    context = ssl.create_default_context()
                    server.starttls(context=context)

            if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)

            server.sendmail(settings.SMTP_SENDER_EMAIL, to_emails, msg.as_string())
            server.quit()

            logger.info(f"Email sent via SMTP to {to_emails}")
            return True
        except Exception as e:
            logger.error(f"SMTP send failed: {str(e)}")
            return False

    def send_verification_email(
        self,
        user_email: str,
        user_name: str,
        verification_token: str,
        base_url: Optional[str] = None,
    ) -> bool:
        """
        Send email verification email

        Args:
            user_email: User's email address
            user_name: User's display name
            verification_token: Email verification token
            base_url: Base URL for verification link

        Returns:
            bool: True if email was sent successfully
        """
        resolved_base_url = base_url or settings.FRONTEND_URL
        verification_url = (
            f"{resolved_base_url}/verify-email?token={verification_token}"
        )

        rendered = self._render_slug(
            "email_verification",
            user_name=user_name,
            user_email=user_email,
            verification_url=verification_url,
        )

        return self._send_email(
            to_emails=[user_email],
            subject=rendered["subject"],
            html_body=rendered["html_body"],
        )

    def send_password_reset_email(
        self,
        user_email: str,
        user_name: str,
        reset_token: str,
        base_url: Optional[str] = None,
    ) -> bool:
        """
        Send password reset email

        Args:
            user_email: User's email address
            user_name: User's display name
            reset_token: Password reset token
            base_url: Base URL for reset link

        Returns:
            bool: True if email was sent successfully
        """
        resolved_base_url = base_url or settings.FRONTEND_URL
        reset_url = f"{resolved_base_url}/reset-password?token={reset_token}"

        rendered = self._render_slug(
            "password_reset",
            user_name=user_name,
            user_email=user_email,
            reset_url=reset_url,
        )

        return self._send_email(
            to_emails=[user_email],
            subject=rendered["subject"],
            html_body=rendered["html_body"],
        )

    def send_welcome_email(
        self,
        user_email: str,
        user_name: str,
        dashboard_url: Optional[str] = None,
    ) -> bool:
        """
        Send welcome email after successful registration

        Args:
            user_email: User's email address
            user_name: User's display name
            dashboard_url: URL to the user dashboard

        Returns:
            bool: True if email was sent successfully
        """
        resolved_dashboard_url = dashboard_url or f"{settings.FRONTEND_URL}/dashboard"

        rendered = self._render_slug(
            "welcome",
            user_name=user_name,
            user_email=user_email,
            dashboard_url=resolved_dashboard_url,
        )

        return self._send_email(
            to_emails=[user_email],
            subject=rendered["subject"],
            html_body=rendered["html_body"],
        )

    def send_notification_email(
        self,
        to_emails: List[str],
        subject: str,
        message: str,
        user_name: Optional[str] = None,
    ) -> bool:
        """
        Send a general notification email

        Args:
            to_emails: List of recipient email addresses
            subject: Email subject
            message: Email message content
            user_name: Optional user name for personalization

        Returns:
            bool: True if email was sent successfully
        """
        greeting = f"Hello {user_name}," if user_name else "Hello,"

        rendered = self._render_slug(
            "notification",
            subject=subject,
            greeting=greeting,
            message=Markup(message) if message else "",
            user_name=user_name or "",
            user_email=to_emails[0] if to_emails else "",
        )

        return self._send_email(
            to_emails=to_emails,
            subject=rendered["subject"],
            html_body=rendered["html_body"],
        )

    def verify_email_address(self, email: str) -> bool:
        """
        Verify an email address with Amazon SES

        Args:
            email: Email address to verify

        Returns:
            bool: True if verification was initiated successfully
        """
        if not self.ses_client:
            logger.error("SES client not initialized. Cannot verify email.")
            return False

        try:
            self.ses_client.verify_email_identity(EmailAddress=email)
            logger.info(f"Email verification initiated for {email}")
            return True
        except ClientError as e:
            logger.error(f"Failed to verify email {email}: {str(e)}")
            return False

    def render_registration_approved_email(
        self,
        *,
        to_email: str,
        user_name: str,
        organization_name: str,
        approver_name: str,
        temp_password: str,
        sign_in_url: str,
    ) -> Dict[str, Any]:
        """Build org registration approval email with credentials (no network I/O)."""
        rendered = self._render_slug(
            "registration_approved",
            user_email=to_email,
            user_name=user_name,
            organization_name=organization_name,
            approver_name=approver_name,
            temp_password=temp_password,
            sign_in_url=sign_in_url,
        )
        text_body = (
            f"{approver_name} approved your registration for {organization_name} "
            f"on {settings.PROJECT_NAME}.\n\n"
            f"Sign in: {sign_in_url}\n\n"
            f"Email: {to_email}\n"
            f"Temporary password: {temp_password}\n\n"
            f"You will be asked to set a new password after signing in.\n"
        )

        return {
            "to_email": to_email,
            "subject": rendered["subject"],
            "html_body": rendered["html_body"],
            "text_body": text_body,
        }

    async def send_registration_approved_email_async(self, rendered: Dict[str, Any]) -> bool:
        return await self._send_in_thread(
            self._send_email,
            to_emails=[rendered["to_email"]],
            subject=rendered["subject"],
            html_body=rendered["html_body"],
            text_body=rendered.get("text_body"),
        )

    def render_invitation_email(
        self,
        to_email: str,
        organization_name: str,
        inviter_name: str,
        invite_url: str,
        role: str,
        team_name: Optional[str] = None,
        temp_password: Optional[str] = None,
        *,
        is_resend: bool = False,
    ) -> Dict[str, Any]:
        """Build invitation email content (no network I/O)."""
        rendered = self._render_slug(
            "invitation",
            user_email=to_email,
            organization_name=organization_name,
            inviter_name=inviter_name,
            invite_url=invite_url,
            role=role,
            team_name=team_name or "No team assigned",
            temp_password=temp_password,
            is_resend=is_resend,
        )

        team_line = team_name or "No team assigned"
        text_body = (
            f"{inviter_name} invited you to join {organization_name} on {settings.PROJECT_NAME}.\n\n"
            f"Role: {role}\n"
            f"Team: {team_line}\n\n"
            f"Accept invitation: {invite_url}\n"
        )
        if temp_password:
            text_body += (
                f"\nSign in with:\n"
                f"Email: {to_email}\n"
                f"Temporary password: {temp_password}\n\n"
                f"You will be asked to set a new password after signing in.\n"
            )

        return {
            "to_email": to_email,
            "subject": rendered["subject"],
            "html_body": rendered["html_body"],
            "text_body": text_body,
        }

    async def send_invitation_email(
        self,
        to_email: str,
        organization_name: str,
        inviter_name: str,
        invite_url: str,
        role: str,
        team_name: Optional[str] = None,
        temp_password: Optional[str] = None,
        *,
        is_resend: bool = False,
    ) -> bool:
        """
        Send organization invitation email with temporary password

        Args:
            to_email: Email address to send invitation to
            organization_name: Name of the organization
            inviter_name: Name of person sending invitation
            invite_url: URL to accept invitation
            role: User role (rep, manager, admin)
            team_name: Optional team name
            temp_password: Temporary password for initial login

        Returns:
            bool: True if email was sent successfully
        """
        rendered = self.render_invitation_email(
            to_email=to_email,
            organization_name=organization_name,
            inviter_name=inviter_name,
            invite_url=invite_url,
            role=role,
            team_name=team_name,
            temp_password=temp_password,
            is_resend=is_resend,
        )

        return await self._send_in_thread(
            self._send_email,
            to_emails=[rendered["to_email"]],
            subject=rendered["subject"],
            html_body=rendered["html_body"],
            text_body=rendered["text_body"],
        )

    def render_manager_note_email(
        self,
        *,
        rep_email: str,
        rep_name: str,
        manager_name: str,
        customer_name: str,
        opportunity_name: str,
        session_url: str,
        note_type: str,
        note_preview: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Build manager-note notification email content (no network I/O)."""
        rendered = self._render_slug(
            "manager_note",
            rep_email=rep_email,
            rep_name=rep_name,
            manager_name=manager_name,
            customer_name=customer_name,
            opportunity_name=opportunity_name,
            session_url=session_url,
            note_type=note_type,
            note_preview=note_preview,
        )

        deal_label = f"{customer_name} — {opportunity_name}"
        if note_type == "audio":
            text_body = (
                f"{manager_name} left an audio coaching note on your session for {deal_label}.\n\n"
                f"View session: {session_url}\n"
            )
        else:
            preview_line = f"\n\nNote preview:\n{note_preview}\n" if note_preview else "\n"
            text_body = (
                f"{manager_name} left a coaching note on your session for {deal_label}."
                f"{preview_line}\n"
                f"View session: {session_url}\n"
            )

        return {
            "to_email": rep_email,
            "subject": rendered["subject"],
            "html_body": rendered["html_body"],
            "text_body": text_body,
        }

    async def send_manager_note_email_async(self, rendered: Dict[str, Any]) -> bool:
        return await self._send_in_thread(
            self._send_email,
            to_emails=[rendered["to_email"]],
            subject=rendered["subject"],
            html_body=rendered["html_body"],
            text_body=rendered.get("text_body"),
        )

    def get_send_quota(self) -> Dict[str, Any]:
        """
        Get the current send quota for the AWS account

        Returns:
            dict: Send quota information including daily limit and current usage
        """
        if not self.ses_client:
            return {"error": "SES client not initialized"}

        try:
            response = self.ses_client.get_send_quota()
            return {
                "max_24_hour_send": response["Max24HourSend"],
                "max_send_rate": response["MaxSendRate"],
                "sent_last_24_hours": response["SentLast24Hours"],
            }
        except ClientError as e:
            return {"error": str(e)}


# Global email service instance
email_service = EmailService()


def get_email_service() -> EmailService:
    """Get the global email service instance"""
    return email_service
