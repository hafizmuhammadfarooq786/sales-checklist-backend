"""
Admin API Endpoints - SYSTEM_ADMIN only
Handles organization and user management across all organizations
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from typing import List, Optional

from app.db.session import get_db
from app.models import Organization, User, Team, OrganizationSettings
from app.models.user import UserRole
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationUpdate,
    OrganizationResponse,
)
from app.schemas.user import UserResponse, UserUpdate
from app.api.dependencies import require_roles

router = APIRouter()


# ==================== ORGANIZATIONS ====================

@router.get("/organizations", response_model=List[OrganizationResponse])
async def list_organizations(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SYSTEM_ADMIN))
):
    """
    List all organizations (SYSTEM_ADMIN only).

    Supports pagination and filtering by:
    - search: Search by organization name
    - is_active: Filter by active status
    """
    query = select(Organization)

    # Apply filters
    if search:
        query = query.where(Organization.name.ilike(f"%{search}%"))
    if is_active is not None:
        query = query.where(Organization.is_active == is_active)

    # Apply pagination and ordering
    query = query.order_by(Organization.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    organizations = result.scalars().all()

    return [OrganizationResponse.model_validate(org) for org in organizations]


@router.post("/organizations", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    organization_data: OrganizationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SYSTEM_ADMIN))
):
    """
    Create a new organization (SYSTEM_ADMIN only).

    Also creates default organization settings.
    """
    # Check if organization name already exists
    existing_org = await db.execute(
        select(Organization).where(Organization.name == organization_data.name)
    )
    if existing_org.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Organization with name '{organization_data.name}' already exists"
        )

    # Create organization
    new_org = Organization(**organization_data.model_dump())
    db.add(new_org)
    await db.flush()
    await db.refresh(new_org)

    # Create default organization settings
    org_settings = OrganizationSettings(
        organization_id=new_org.id,
        allow_self_registration=False,
        default_role="rep",
        settings={}
    )
    db.add(org_settings)

    await db.commit()
    await db.refresh(new_org)

    return OrganizationResponse.model_validate(new_org)


@router.get("/organizations/{org_id}", response_model=OrganizationResponse)
async def get_organization(
    org_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SYSTEM_ADMIN))
):
    """
    Get organization details by ID (SYSTEM_ADMIN only).
    """
    result = await db.execute(
        select(Organization).where(Organization.id == org_id)
    )
    organization = result.scalar_one_or_none()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization with ID {org_id} not found"
        )

    return OrganizationResponse.model_validate(organization)


@router.patch("/organizations/{org_id}", response_model=OrganizationResponse)
async def update_organization(
    org_id: int,
    organization_data: OrganizationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SYSTEM_ADMIN))
):
    """
    Update organization details (SYSTEM_ADMIN only).
    """
    result = await db.execute(
        select(Organization).where(Organization.id == org_id)
    )
    organization = result.scalar_one_or_none()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization with ID {org_id} not found"
        )

    # Update fields
    update_data = organization_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(organization, field, value)

    await db.commit()
    await db.refresh(organization)

    return OrganizationResponse.model_validate(organization)


@router.delete("/organizations/{org_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization(
    org_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SYSTEM_ADMIN))
):
    """
    Delete an organization (SYSTEM_ADMIN only).

    WARNING: This will cascade delete all teams, users, and data associated with this organization.
    """
    result = await db.execute(
        select(Organization).where(Organization.id == org_id)
    )
    organization = result.scalar_one_or_none()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization with ID {org_id} not found"
        )

    # Check if organization has users
    user_count_result = await db.execute(
        select(func.count(User.id)).where(User.organization_id == org_id)
    )
    user_count = user_count_result.scalar() or 0

    if user_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete organization with {user_count} active users. Remove users first."
        )

    await db.delete(organization)
    await db.commit()


# ==================== USERS ====================

@router.get("/users", response_model=List[UserResponse])
async def list_all_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = None,
    organization_id: Optional[int] = None,
    team_id: Optional[int] = None,
    role: Optional[UserRole] = None,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SYSTEM_ADMIN))
):
    """
    List all users across all organizations (SYSTEM_ADMIN only).

    Supports pagination and filtering by:
    - search: Search by email, first_name, or last_name
    - organization_id: Filter by organization
    - team_id: Filter by team
    - role: Filter by role
    - is_active: Filter by active status
    """
    query = select(User).options(
        selectinload(User.organization),
        selectinload(User.team)
    )

    # Apply filters
    if search:
        search_filter = or_(
            User.email.ilike(f"%{search}%"),
            User.first_name.ilike(f"%{search}%"),
            User.last_name.ilike(f"%{search}%")
        )
        query = query.where(search_filter)

    if organization_id is not None:
        query = query.where(User.organization_id == organization_id)

    if team_id is not None:
        query = query.where(User.team_id == team_id)

    if role is not None:
        query = query.where(User.role == role)

    if is_active is not None:
        query = query.where(User.is_active == is_active)

    # Apply pagination and ordering
    query = query.order_by(User.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    users = result.scalars().all()

    return [UserResponse.model_validate(user) for user in users]


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SYSTEM_ADMIN))
):
    """
    Get user details by ID (SYSTEM_ADMIN only).
    """
    result = await db.execute(
        select(User)
        .options(selectinload(User.organization), selectinload(User.team))
        .where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )

    return UserResponse.model_validate(user)


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SYSTEM_ADMIN))
):
    """
    Update user details (SYSTEM_ADMIN only).

    Can update organization_id, team_id, role, and other user fields.
    """
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )

    # Update fields
    update_data = user_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)

    return UserResponse.model_validate(user)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SYSTEM_ADMIN))
):
    """
    Delete a user (SYSTEM_ADMIN only).

    WARNING: This will delete the user and may affect associated sessions and data.
    """
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )

    # Prevent deleting yourself
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own user account"
        )

    await db.delete(user)
    await db.commit()


# ==================== STATISTICS ====================

@router.get("/stats")
async def get_system_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SYSTEM_ADMIN))
):
    """
    Get system-wide statistics (SYSTEM_ADMIN only).

    Returns:
    - Total organizations count
    - Total users count
    - Total teams count
    - Active organizations count
    - Active users count
    """
    # Count organizations
    org_count_result = await db.execute(select(func.count(Organization.id)))
    total_orgs = org_count_result.scalar() or 0

    active_org_count_result = await db.execute(
        select(func.count(Organization.id)).where(Organization.is_active == True)
    )
    active_orgs = active_org_count_result.scalar() or 0

    # Count users
    user_count_result = await db.execute(select(func.count(User.id)))
    total_users = user_count_result.scalar() or 0

    active_user_count_result = await db.execute(
        select(func.count(User.id)).where(User.is_active == True)
    )
    active_users = active_user_count_result.scalar() or 0

    # Count teams
    team_count_result = await db.execute(select(func.count(Team.id)))
    total_teams = team_count_result.scalar() or 0

    return {
        "total_organizations": total_orgs,
        "active_organizations": active_orgs,
        "total_users": total_users,
        "active_users": active_users,
        "total_teams": total_teams
    }
