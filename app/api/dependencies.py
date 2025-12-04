"""
API Dependencies for authentication and authorization
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from app.db.session import get_db
from app.models.user import User, UserRole
from app.services.auth_service import auth_service
from app.core.config import settings


security = HTTPBearer(auto_error=False)


async def get_current_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> int:
    """
    Get current user ID from JWT token.
    Validates JWT token and extracts user_id.

    SECURITY: Always requires valid JWT token - no bypasses in any environment.
    """

    # Validate JWT token is provided
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Decode and validate JWT token
    payload = auth_service.decode_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id: str = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        return int(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token",
            headers={"WWW-Authenticate": "Bearer"},
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


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get the current authenticated and active user.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    
    return current_user


def require_roles(*roles: UserRole):
    """
    Dependency factory for role-based access control.
    Usage: @app.get("/admin", dependencies=[Depends(require_roles(UserRole.ADMIN))])
    """
    def check_user_role(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return current_user

    return check_user_role


def get_session_access_filter(current_user: User):
    """
    Build SQLAlchemy filter conditions based on user role for session access.

    Role-Based Access Logic:
    - ADMIN: Can access ALL sessions in their organization
    - MANAGER: Can access sessions from users in their team
    - REP: Can only access their own sessions

    Returns:
        SQLAlchemy filter condition to be used in WHERE clause
    """
    from app.models.session import Session

    if current_user.role == UserRole.ADMIN:
        # Admin sees all sessions in their organization
        if current_user.organization_id:
            # Filter by organization - get all users in org, then their sessions
            return Session.user.has(organization_id=current_user.organization_id)
        else:
            # No organization assigned - only see own sessions
            return Session.user_id == current_user.id

    elif current_user.role == UserRole.MANAGER:
        # Manager sees team sessions
        if current_user.team_id:
            # Filter by team - get all users in team, then their sessions
            return Session.user.has(team_id=current_user.team_id)
        else:
            # No team assigned - only see own sessions
            return Session.user_id == current_user.id

    else:  # REP or any other role
        # Rep sees only own sessions
        return Session.user_id == current_user.id


async def check_session_access(
    session_id: int,
    current_user: User,
    db: AsyncSession
) -> bool:
    """
    Check if current user has access to a specific session based on their role.

    Args:
        session_id: The session ID to check access for
        current_user: The current authenticated user
        db: Database session

    Returns:
        True if user has access, False otherwise
    """
    from app.models.session import Session

    # Build query with role-based filter
    access_filter = get_session_access_filter(current_user)

    result = await db.execute(
        select(Session).where(
            Session.id == session_id,
            access_filter
        )
    )

    session = result.scalar_one_or_none()
    return session is not None
