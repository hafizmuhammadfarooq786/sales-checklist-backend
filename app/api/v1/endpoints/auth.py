from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from app.db.session import get_db
from app.models.user import User
from app.schemas.user import (
    UserCreate, Token, EmailVerification, UserResponse,
    EmailRequest, OtpRequest, OtpVerify,
)
from app.services.auth_service import auth_service
from app.services.auth_session_service import auth_session_service
from app.services.otp_service import otp_service, GENERIC_OTP_MESSAGE
from app.services.activity_emitter import activity_emitter
from app.services import activity_event_types as evt
from app.services.email_dispatch import (
    dispatch_login_otp_email,
    dispatch_verification_email,
    dispatch_welcome_email,
)
from app.api.dependencies import get_current_active_user, security
from app.core.config import settings
from app.core.request_context import client_ip_from_request
from app.models.user import UserRole


def _client_ip(request: Request) -> str | None:
    return client_ip_from_request(request)

logger = logging.getLogger(__name__)


class RegisterResponse(BaseModel):
    message: str


router = APIRouter(prefix="/auth", tags=["Authentication"])


# Register a new user account
@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
) -> RegisterResponse:
    """
    Register a new user account (disabled in invite-only mode).
    """
    if not settings.ALLOW_PUBLIC_SIGNUP:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Public signup is disabled. Ask your organization admin for an invitation."
        )

    if user_data.role != UserRole.REP:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Public signup can only create REP users."
        )
    
    # Check if user already exists
    result = await db.execute(
        select(User).where(User.email == user_data.email)
    )
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user. auth_service.create_user already sends the verification
    # email (and rolls back on failure), so we do not send it again here.
    try:
        await auth_service.create_user(db, user_data)

        return RegisterResponse(
            message="Registration successful. Please verify your email before logging in."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"User registration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user account"
        )


async def _issue_session_token(
    *,
    user: User,
    request: Request,
    db: AsyncSession,
    remember_me: bool,
) -> Token:
    """Create a JWT and auth_session. Each device gets its own session."""
    jti = auth_session_service.new_jti()
    expires_at = auth_service.token_expiry_datetime(remember_me=remember_me)
    token_response = await auth_service.create_token_response(
        user, remember_me=remember_me, jti=jti
    )
    await auth_session_service.create_session(
        db,
        user=user,
        jti=jti,
        expires_at=expires_at,
        remember_me=remember_me,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    await activity_emitter.emit(
        db,
        event_type=evt.AUTH_LOGIN,
        organization_id=user.organization_id,
        actor_user_id=user.id,
        resource_type="auth_session",
        resource_id=jti,
        payload={"remember_me": remember_me, "role": user.role.value, "method": "otp"},
        commit=True,
    )
    return token_response


@router.post("/otp/request", status_code=status.HTTP_200_OK)
async def request_login_otp(
    otp_request: OtpRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Email a 24-hour login OTP. Always returns a generic message.
    Issuing a new code revokes any previous active code for that user.
    """
    from datetime import datetime

    user = await otp_service.get_active_user_by_email(db, otp_request.email)
    locked = bool(user and user.locked_until and user.locked_until > datetime.utcnow())
    if not user:
        logger.info(
            "OTP not sent: no active account for %s",
            otp_request.email.strip().lower(),
        )
    elif locked:
        logger.info("OTP not sent: account locked for %s", user.email)
    if user and not locked:
        code = await otp_service.issue_code(
            db, user, ip_address=_client_ip(request)
        )
        if code:
            await db.commit()
            user_name = (
                f"{user.first_name or ''} {user.last_name or ''}".strip()
                or user.email
            )
            try:
                email_sent = await dispatch_login_otp_email(
                    user_email=user.email,
                    user_name=user_name,
                    otp_code=code,
                )
                if email_sent:
                    logger.info("Login OTP emailed to %s", user.email)
                else:
                    logger.warning("Failed to send login OTP to %s", user.email)
            except Exception as email_error:
                logger.error("Login OTP email error: %s", email_error)
            await activity_emitter.emit(
                db,
                event_type=evt.AUTH_OTP_REQUESTED,
                organization_id=user.organization_id,
                actor_user_id=user.id,
                resource_type="user",
                resource_id=user.id,
                commit=True,
            )
        else:
            await db.commit()
    return {"message": GENERIC_OTP_MESSAGE}


@router.post("/otp/verify", response_model=Token)
async def verify_login_otp(
    otp_data: OtpVerify,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Token:
    """
    Verify a login OTP and issue a JWT. The same code can be used on
    additional devices until it expires or a new code is requested.
    """
    user, error = await otp_service.verify_code(db, otp_data.email, otp_data.code)
    if not user:
        await activity_emitter.emit(
            db,
            event_type=evt.AUTH_OTP_FAILED,
            payload={"email": otp_data.email},
            commit=True,
        )
        detail = (
            "Too many failed attempts. Try again later."
            if error == "locked"
            else "Invalid or expired verification code"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )

    return await _issue_session_token(
        user=user,
        request=request,
        db=db,
        remember_me=bool(otp_data.remember_me),
    )


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Revoke the current auth session (jti). Safe to call even if already revoked.
    """
    if not credentials:
        return {"message": "Logged out"}

    payload = auth_service.decode_access_token(credentials.credentials)
    jti = payload.get("jti") if payload else None
    user_id = None
    org_id = None
    if payload and payload.get("sub"):
        try:
            user_id = int(payload["sub"])
        except (TypeError, ValueError):
            user_id = None
    if jti:
        session = await auth_session_service.revoke_session(db, jti)
        if session:
            org_id = session.organization_id
            user_id = user_id or session.user_id
    await activity_emitter.emit(
        db,
        event_type=evt.AUTH_LOGOUT,
        organization_id=org_id,
        actor_user_id=user_id,
        resource_type="auth_session",
        resource_id=jti,
        commit=True,
    )
    return {"message": "Logged out"}


# Verify user email address with token
@router.post("/verify-email", status_code=status.HTTP_200_OK)
async def verify_email(
    verification_data: EmailVerification,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Verify user email address with token.
    """
    
    user = await auth_service.verify_email(db, verification_data.token)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token"
        )
    
    # Send welcome email after successful verification
    try:
        user_name = f"{user.first_name or ''} {user.last_name or ''}".strip() or user.email
        email_sent = await dispatch_welcome_email(
            user_email=user.email,
            user_name=user_name
        )
        if email_sent:
            logger.info(f"Welcome email sent to {user.email}")
        else:
            logger.warning(f"Failed to send welcome email to {user.email}")
    except Exception as email_error:
        logger.error(f"Welcome email error: {str(email_error)}")
    
    return {"message": "Email verified successfully"}


# Resend email verification link
@router.post("/resend-verification", status_code=status.HTTP_200_OK)
async def resend_verification_email(
    email_request: EmailRequest,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Resend email verification link.
    Always returns success to prevent email enumeration attacks.
    """
    
    result = await db.execute(select(User).where(User.email == email_request.email))
    user = result.scalar_one_or_none()
    
    if user and not user.is_verified:
        try:
            user = await auth_service.generate_email_verification_token(db, user)
            
            if user and user.email_verification_token:
                user_name = f"{user.first_name or ''} {user.last_name or ''}".strip() or user.email
                email_sent = await dispatch_verification_email(
                    user_email=user.email,
                    user_name=user_name,
                    verification_token=user.email_verification_token
                )
                if email_sent:
                    logger.info(f"Verification email resent to {user.email}")
                else:
                    logger.warning(f"Failed to resend verification email to {user.email}")
        except Exception as email_error:
            logger.error(f"Resend verification email error: {str(email_error)}")
    
    return {
        "message": "If the email exists and is unverified, a new verification link has been sent"
    }


# Get current authenticated user information
@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
) -> UserResponse:
    """
    Get current authenticated user information.
    """

    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        role=current_user.role,
        organization_id=current_user.organization_id,
        team_id=current_user.team_id,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        last_login=current_user.last_login,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at
    )