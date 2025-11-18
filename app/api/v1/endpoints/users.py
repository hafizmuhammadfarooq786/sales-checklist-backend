"""
User API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models import User, Team, Organization
from app.schemas.user import (
    UserResponse,
    UserUpdate,
    TeamResponse,
    OrganizationResponse,
)

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    user_id: int,  # TODO: Get from JWT token
    db: AsyncSession = Depends(get_db)
):
    """
    Get current authenticated user's profile.
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

    return UserResponse.model_validate(user)


@router.patch("/me", response_model=UserResponse)
async def update_current_user(
    user_data: UserUpdate,
    user_id: int,  # TODO: Get from JWT token
    db: AsyncSession = Depends(get_db)
):
    """
    Update current user's profile.
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

    # Update fields
    update_data = user_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)

    return UserResponse.model_validate(user)


@router.get("/me/team", response_model=TeamResponse)
async def get_current_user_team(
    user_id: int,  # TODO: Get from JWT token
    db: AsyncSession = Depends(get_db)
):
    """
    Get current user's team information.
    """
    result = await db.execute(
        select(User).where(User.id == user_id).options(selectinload(User.team))
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if not user.team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not assigned to a team"
        )

    return TeamResponse.model_validate(user.team)


@router.get("/me/organization", response_model=OrganizationResponse)
async def get_current_user_organization(
    user_id: int,  # TODO: Get from JWT token
    db: AsyncSession = Depends(get_db)
):
    """
    Get current user's organization information.
    """
    result = await db.execute(
        select(User).where(User.id == user_id).options(selectinload(User.organization))
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if not user.organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not assigned to an organization"
        )

    return OrganizationResponse.model_validate(user.organization)
