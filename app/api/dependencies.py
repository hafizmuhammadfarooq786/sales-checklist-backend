"""
API Dependencies for authentication and authorization
"""
from fastapi import Depends, HTTPException, Header, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from app.db.session import get_db
from app.models import User
from app.core.config import settings


async def get_current_user_id(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
) -> int:
    """
    Get current user ID from JWT token.
    For development: If no token is provided, use/create a test user.
    For production: Validate Clerk JWT token and extract user_id.
    """

    # TODO: Implement proper Clerk JWT verification
    # For now, use a development test user
    if settings.ENVIRONMENT == "development":
        # Try to get or create test user
        result = await db.execute(
            select(User).where(User.email == "test@example.com")
        )
        user = result.scalar_one_or_none()

        if not user:
            # Create test user for development
            from app.models.user import UserRole
            user = User(
                email="test@example.com",
                clerk_user_id="test_clerk_user_id",
                first_name="Test",
                last_name="User",
                role=UserRole.REP,
                is_active=True
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)

        return user.id

    # Production: Validate JWT token
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header"
        )

    # TODO: Implement Clerk JWT token verification
    # This should verify the token with Clerk and extract the user_id
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="JWT authentication not yet implemented"
    )


async def get_current_user(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get the current authenticated user object.
    """
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return user
