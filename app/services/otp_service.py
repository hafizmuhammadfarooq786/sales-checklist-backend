"""
Passwordless login OTP: generate, store, revoke, and verify email codes.
"""

import hashlib
import hmac
import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.login_otp import LoginOtp
from app.models.user import User

logger = logging.getLogger(__name__)

GENERIC_OTP_MESSAGE = (
    "If an account exists for this email, a verification code has been sent."
)


class OtpService:
    """Email OTP lifecycle for passwordless sign-in."""

    def generate_code(self) -> str:
        return f"{secrets.randbelow(1_000_000):06d}"

    def hash_code(self, code: str) -> str:
        return hmac.new(
            settings.SECRET_KEY.encode("utf-8"),
            code.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def codes_match(self, code: str, code_hash: str) -> bool:
        return hmac.compare_digest(self.hash_code(code), code_hash)

    def normalize_code(self, code: str) -> str:
        return "".join(ch for ch in (code or "") if ch.isdigit())

    async def get_active_user_by_email(
        self, db: AsyncSession, email: str
    ) -> Optional[User]:
        result = await db.execute(
            select(User)
            .options(selectinload(User.organization), selectinload(User.team))
            .where(
                func.lower(User.email) == email.strip().lower(),
                User.is_active.is_(True),
                User.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def revoke_active_for_user(self, db: AsyncSession, user_id: int) -> int:
        result = await db.execute(
            update(LoginOtp)
            .where(LoginOtp.user_id == user_id, LoginOtp.revoked_at.is_(None))
            .values(revoked_at=datetime.utcnow())
        )
        return result.rowcount or 0

    async def recent_request_count(self, db: AsyncSession, user_id: int) -> int:
        since = datetime.utcnow() - timedelta(hours=1)
        result = await db.execute(
            select(func.count(LoginOtp.id)).where(
                LoginOtp.user_id == user_id,
                LoginOtp.created_at >= since,
            )
        )
        return int(result.scalar() or 0)

    async def issue_code(
        self,
        db: AsyncSession,
        user: User,
        *,
        ip_address: Optional[str] = None,
    ) -> Optional[str]:
        """
        Revoke any previous active code and create a new 24-hour OTP.

        Returns the plaintext code for emailing, or None if rate-limited.
        """
        if await self.recent_request_count(db, user.id) >= settings.OTP_MAX_REQUESTS_PER_HOUR:
            logger.warning("OTP request rate-limited for user_id=%s", user.id)
            return None

        await self.revoke_active_for_user(db, user.id)

        code = self.generate_code()
        otp = LoginOtp(
            user_id=user.id,
            code_hash=self.hash_code(code),
            expires_at=datetime.utcnow() + timedelta(hours=settings.OTP_EXPIRE_HOURS),
            created_at=datetime.utcnow(),
            ip_address=ip_address,
        )
        db.add(otp)
        await db.flush()
        return code

    async def verify_code(
        self, db: AsyncSession, email: str, code: str
    ) -> Tuple[Optional[User], str]:
        """
        Verify an OTP without consuming it, so the same code can sign in
        additional devices until it expires or is revoked by a resend.

        Returns (user, error_code). error_code is empty on success.
        """
        normalized = self.normalize_code(code)
        if len(normalized) != 6:
            return None, "invalid"

        user = await self.get_active_user_by_email(db, email)
        if not user:
            return None, "invalid"

        if user.locked_until and user.locked_until > datetime.utcnow():
            return None, "locked"

        result = await db.execute(
            select(LoginOtp)
            .where(
                LoginOtp.user_id == user.id,
                LoginOtp.revoked_at.is_(None),
                LoginOtp.expires_at > datetime.utcnow(),
            )
            .order_by(LoginOtp.created_at.desc())
        )
        otp = result.scalars().first()
        if not otp or not self.codes_match(normalized, otp.code_hash):
            user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
            if user.failed_login_attempts >= 5:
                user.locked_until = datetime.utcnow() + timedelta(minutes=30)
            await db.flush()
            return None, "invalid"

        otp.last_used_at = datetime.utcnow()
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login = datetime.utcnow()
        await db.flush()
        return user, ""


otp_service = OtpService()
