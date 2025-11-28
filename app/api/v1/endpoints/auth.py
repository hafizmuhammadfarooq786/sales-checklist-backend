"""
Authentication endpoints for login, registration, and password management
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from app.db.session import get_db
from app.models.user import User
from app.schemas.user import (
    UserCreate, UserLogin, Token, PasswordReset,
    PasswordResetConfirm, EmailVerification, UserResponse,
    PasswordChange
)
from app.services.auth_service import auth_service
from app.services.email_service import email_service
from app.api.dependencies import get_current_active_user

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
) -> Token:
    """
    Register a new user account.
    
    Creates a new user with hashed password and sends email verification.
    Returns JWT token for immediate login.
    """
    
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
    
    # Create new user
    try:
        user = await auth_service.create_user(db, user_data)
        token_response = await auth_service.create_token_response(user)
        
        # Send email verification email
        if user.email_verification_token:
            try:
                user_name = f"{user.first_name or ''} {user.last_name or ''}".strip() or user.email
                email_sent = email_service.send_verification_email(
                    user_email=user.email,
                    user_name=user_name,
                    verification_token=user.email_verification_token
                )
                if email_sent:
                    logger.info(f"Verification email sent to {user.email}")
                else:
                    logger.warning(f"Failed to send verification email to {user.email}")
            except Exception as email_error:
                logger.error(f"Email service error: {str(email_error)}")
                # Don't fail registration if email fails
        
        return token_response
        
    except Exception as e:
        logger.error(f"User registration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user account"
        )


@router.post("/login", response_model=Token)
async def login(
    user_credentials: UserLogin,
    db: AsyncSession = Depends(get_db)
) -> Token:
    """
    Authenticate user and return JWT token.
    
    Validates email/password combination and returns access token.
    Implements account locking after failed attempts.
    """
    
    user = await auth_service.authenticate_user(
        db, user_credentials.email, user_credentials.password
    )
    
    if not user:
        # Don't reveal whether email exists or password is wrong
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user is verified (optional - can be disabled for MVP)
    # if not user.is_verified:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Email not verified. Please check your email."
    #     )
    
    token_response = await auth_service.create_token_response(user)
    return token_response


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
        email_sent = email_service.send_welcome_email(
            user_email=user.email,
            user_name=user_name
        )
        if email_sent:
            logger.info(f"Welcome email sent to {user.email}")
        else:
            logger.warning(f"Failed to send welcome email to {user.email}")
    except Exception as email_error:
        logger.error(f"Welcome email error: {str(email_error)}")
        # Don't fail verification if welcome email fails
    
    return {"message": "Email verified successfully"}


@router.post("/resend-verification", status_code=status.HTTP_200_OK)
async def resend_verification_email(
    email_request: PasswordReset,  # Reuse the PasswordReset schema which has email field
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Resend email verification link.
    
    Always returns success to prevent email enumeration attacks.
    """
    
    # Find user by email
    result = await db.execute(select(User).where(User.email == email_request.email))
    user = result.scalar_one_or_none()
    
    # Only send if user exists and is not already verified
    if user and not user.is_verified:
        try:
            # Generate new verification token
            user = await auth_service.generate_email_verification_token(db, user)
            
            if user and user.email_verification_token:
                user_name = f"{user.first_name or ''} {user.last_name or ''}".strip() or user.email
                email_sent = email_service.send_verification_email(
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


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
async def forgot_password(
    reset_request: PasswordReset,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Request password reset token.
    
    Always returns success to prevent email enumeration attacks.
    """
    
    # Always return success, even if email doesn't exist
    # This prevents email enumeration attacks
    user = await auth_service.request_password_reset(db, reset_request.email)
    
    # Send password reset email only if user exists
    if user and user.password_reset_token:
        try:
            user_name = f"{user.first_name or ''} {user.last_name or ''}".strip() or user.email
            email_sent = email_service.send_password_reset_email(
                user_email=user.email,
                user_name=user_name,
                reset_token=user.password_reset_token
            )
            if email_sent:
                logger.info(f"Password reset email sent to {user.email}")
            else:
                logger.warning(f"Failed to send password reset email to {user.email}")
        except Exception as email_error:
            logger.error(f"Password reset email error: {str(email_error)}")
            # Don't reveal the error to prevent enumeration
    
    return {
        "message": "If the email exists, a password reset link has been sent"
    }


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(
    reset_data: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Reset password with token.
    """
    
    success = await auth_service.reset_password(
        db, reset_data.token, reset_data.new_password
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    return {"message": "Password reset successfully"}


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


@router.post("/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Change password for authenticated user.

    Requires current password verification for security.
    Prevents same password from being used again.
    """

    # Check if new password is same as current password
    if auth_service.verify_password(password_data.new_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from current password"
        )

    # Change password (verifies current password internally)
    success = await auth_service.change_password(
        db, current_user, password_data.current_password, password_data.new_password
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    logger.info(f"Password changed successfully for user {current_user.email}")

    return {"message": "Password changed successfully"}


