"""
User API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, distinct
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models import User, Team, Organization
from app.models.session import Session, SessionStatus
from app.schemas.user import (
    UserResponse,
    UserUpdate,
    TeamResponse,
    OrganizationResponse,
    PipelineMetrics,
)
from app.api.dependencies import get_current_user_id, get_current_user

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """
    Get current authenticated user's profile.
    """
    return UserResponse.model_validate(current_user)


@router.patch("/me", response_model=UserResponse)
async def update_current_user(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update current user's profile.
    """
    # Update fields
    update_data = user_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(current_user, field, value)

    await db.commit()
    await db.refresh(current_user)

    return UserResponse.model_validate(current_user)


@router.get("/me/team", response_model=TeamResponse)
async def get_current_user_team(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current user's team information.
    """
    # Load team relationship if not already loaded
    if current_user.team_id:
        result = await db.execute(
            select(User).where(User.id == current_user.id).options(selectinload(User.team))
        )
        user_with_team = result.scalar_one_or_none()
        if user_with_team and user_with_team.team:
            return TeamResponse.model_validate(user_with_team.team)

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User is not assigned to a team"
    )


@router.get("/me/organization", response_model=OrganizationResponse)
async def get_current_user_organization(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current user's organization information.
    """
    # Load organization relationship if not already loaded
    if current_user.organization_id:
        result = await db.execute(
            select(User).where(User.id == current_user.id).options(selectinload(User.organization))
        )
        user_with_org = result.scalar_one_or_none()
        if user_with_org and user_with_org.organization:
            return OrganizationResponse.model_validate(user_with_org.organization)

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User is not assigned to an organization"
    )


@router.get("/me/metrics", response_model=PipelineMetrics)
async def get_current_user_metrics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current user's pipeline metrics.

    Returns aggregated metrics based on user's sessions:
    - Total sessions count
    - Active sessions (in progress, not draft/failed/completed)
    - Completed sessions count
    - Total unique opportunities
    """
    # Get total sessions count
    total_result = await db.execute(
        select(func.count(Session.id)).where(Session.user_id == current_user.id)
    )
    total_sessions = total_result.scalar() or 0

    # Get active sessions (processing, analyzing, scoring, pending_review)
    active_statuses = [
        SessionStatus.UPLOADING,
        SessionStatus.PROCESSING,
        SessionStatus.ANALYZING,
        SessionStatus.SCORING,
        SessionStatus.PENDING_REVIEW
    ]
    active_result = await db.execute(
        select(func.count(Session.id)).where(
            Session.user_id == current_user.id,
            Session.status.in_(active_statuses)
        )
    )
    active_sessions = active_result.scalar() or 0

    # Get completed sessions count
    completed_result = await db.execute(
        select(func.count(Session.id)).where(
            Session.user_id == current_user.id,
            Session.status == SessionStatus.COMPLETED
        )
    )
    completed_sessions = completed_result.scalar() or 0

    # Get total unique opportunities (count distinct opportunity_name where not null)
    opportunities_result = await db.execute(
        select(func.count(distinct(Session.opportunity_name))).where(
            Session.user_id == current_user.id,
            Session.opportunity_name.isnot(None),
            Session.opportunity_name != ""
        )
    )
    total_opportunities = opportunities_result.scalar() or 0

    return PipelineMetrics(
        total_sessions=total_sessions,
        active_sessions=active_sessions,
        completed_sessions=completed_sessions,
        total_opportunities=total_opportunities
    )
