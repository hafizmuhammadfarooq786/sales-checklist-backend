"""
Authentication service for JWT token generation
"""

import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.services.email_dispatch import dispatch_verification_email
from fastapi import HTTPException, status
from app.core.config import settings
from app.models.user import User
from app.schemas.user import UserCreate, Token, UserResponse

logger = logging.getLogger(__name__)


class AuthService:
    """Authentication service for JWT management"""

    def __init__(self):
        self.algorithm = settings.ALGORITHM
        self.secret_key = settings.SECRET_KEY
        self.access_token_expire_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES

    def create_access_token(
        self, data: dict, expires_delta: Optional[timedelta] = None, jti: Optional[str] = None
    ) -> str:
        """Create a JWT access token"""
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=self.access_token_expire_minutes
            )

        to_encode.update({"exp": expire})
        if jti:
            to_encode["jti"] = jti
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def decode_access_token(self, token: str) -> Optional[dict]:
        """Decode and validate a JWT access token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except JWTError:
            return None

    def generate_verification_token(self) -> str:
        """Generate a secure email verification token"""
        return secrets.token_urlsafe(32)

    async def create_user(self, db: AsyncSession, user_data: UserCreate) -> User:
        """Create a new user. Sign-in uses email OTP, not a password."""
        user = User(
            email=user_data.email,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            role=user_data.role,
            is_active=False,  # Activate only after email verification
            email_verification_token=self.generate_verification_token(),
            email_verification_expires=datetime.utcnow() + timedelta(hours=24),
        )

        # Send email verification email
        if user.email_verification_token:
            try:
                user_name = (
                    f"{user.first_name or ''} {user.last_name or ''}".strip()
                    or user.email
                )
                email_sent = await dispatch_verification_email(
                    user_email=user.email,
                    user_name=user_name,
                    verification_token=user.email_verification_token,
                )
                if email_sent:
                    logger.info(f"Verification email sent to {user.email}")
                else:
                    await db.delete(user)
                    await db.commit()
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="Failed to send verification email. Please try again.",
                    )
            except HTTPException:
                raise
            except Exception as email_error:
                logger.error(f"Email service error: {str(email_error)}")
                await db.delete(user)
                await db.commit()

        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    async def create_token_response(
        self,
        user: User,
        remember_me: bool = False,
        jti: Optional[str] = None,
    ) -> Token:
        """Create a complete token response with user data."""
        if remember_me:
            expires_delta = timedelta(days=settings.REMEMBER_ME_TOKEN_EXPIRE_DAYS)
        else:
            expires_delta = timedelta(minutes=settings.SESSION_TOKEN_EXPIRE_MINUTES)

        access_token = self.create_access_token(
            data={"sub": str(user.id), "email": user.email, "role": user.role.value},
            expires_delta=expires_delta,
            jti=jti,
        )

        user_response = UserResponse(
            id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            role=user.role,
            organization_id=user.organization_id,
            team_id=user.team_id,
            is_active=user.is_active,
            is_verified=user.is_verified,
            last_login=user.last_login,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

        return Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=int(expires_delta.total_seconds()),
            user=user_response,
        )

    def token_expiry_datetime(self, remember_me: bool = False) -> datetime:
        if remember_me:
            return datetime.utcnow() + timedelta(days=settings.REMEMBER_ME_TOKEN_EXPIRE_DAYS)
        return datetime.utcnow() + timedelta(minutes=settings.SESSION_TOKEN_EXPIRE_MINUTES)

    async def verify_email(self, db: AsyncSession, token: str) -> Optional[User]:
        """Verify email with token and return the user"""
        result = await db.execute(
            select(User).where(
                and_(
                    User.email_verification_token == token,
                    User.email_verification_expires > datetime.utcnow(),
                )
            )
        )
        user = result.scalar_one_or_none()

        if not user:
            return None

        user.is_verified = True
        user.is_active = True
        user.email_verification_token = None
        user.email_verification_expires = None
        await db.commit()
        await db.refresh(user)
        return user

    async def generate_email_verification_token(
        self, db: AsyncSession, user: User
    ) -> Optional[User]:
        """Generate new email verification token for user"""
        if user.is_verified:
            return None

        user.email_verification_token = self.generate_verification_token()
        user.email_verification_expires = datetime.utcnow() + timedelta(hours=24)
        await db.commit()
        await db.refresh(user)
        return user


# Global auth service instance
auth_service = AuthService()
