"""
Organization API Endpoints - ADMIN level
Handles organization settings, teams, invitations, and user management
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload
from typing import List, Optional

from app.db.session import get_db
from app.models import Organization, User, Team, Invitation, OrganizationSettings
from app.models.user import UserRole
from app.schemas.organization import (
    OrganizationResponse,
    OrganizationSettingsUpdate,
    OrganizationSettingsResponse,
    TeamCreate,
    TeamUpdate,
    TeamResponse,
)
from app.schemas.invitation import (
    InvitationCreate,
    InvitationResponse,
    InvitationVerify,
    InvitationAccept,
)
from app.schemas.user import UserResponse
from app.api.dependencies import require_roles, get_current_user
from app.services.invitation_service import get_invitation_service
from app.core.config import settings

router = APIRouter()
invitation_service = get_invitation_service()


# ==================== ORGANIZATION MANAGEMENT ====================

@router.get("/", response_model=OrganizationResponse)
async def get_my_organization(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER))
):
    """
    Get current user's organization details (ADMIN or MANAGER).
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not assigned to an organization"
        )

    result = await db.execute(
        select(Organization).where(Organization.id == current_user.organization_id)
    )
    organization = result.scalar_one_or_none()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    return OrganizationResponse.model_validate(organization)


@router.get("/settings", response_model=OrganizationSettingsResponse)
async def get_organization_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN))
):
    """
    Get organization settings (ADMIN only).
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not assigned to an organization"
        )

    result = await db.execute(
        select(OrganizationSettings).where(
            OrganizationSettings.organization_id == current_user.organization_id
        )
    )
    org_settings = result.scalar_one_or_none()

    if not org_settings:
        # Create default settings if they don't exist
        org_settings = OrganizationSettings(
            organization_id=current_user.organization_id,
            allow_self_registration=False,
            default_role="rep",
            settings={}
        )
        db.add(org_settings)
        await db.commit()
        await db.refresh(org_settings)

    return OrganizationSettingsResponse.model_validate(org_settings)


@router.patch("/settings", response_model=OrganizationSettingsResponse)
async def update_organization_settings(
    settings_data: OrganizationSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN))
):
    """
    Update organization settings (ADMIN only).
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not assigned to an organization"
        )

    result = await db.execute(
        select(OrganizationSettings).where(
            OrganizationSettings.organization_id == current_user.organization_id
        )
    )
    org_settings = result.scalar_one_or_none()

    if not org_settings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization settings not found"
        )

    # Update fields
    update_data = settings_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(org_settings, field, value)

    await db.commit()
    await db.refresh(org_settings)

    return OrganizationSettingsResponse.model_validate(org_settings)


# ==================== TEAM MANAGEMENT ====================

@router.get("/teams", response_model=List[TeamResponse])
async def list_organization_teams(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER))
):
    """
    List all teams in the organization (ADMIN or MANAGER).
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not assigned to an organization"
        )

    query = select(Team).where(Team.organization_id == current_user.organization_id)

    # Apply search filter
    if search:
        query = query.where(Team.name.ilike(f"%{search}%"))

    # Apply pagination and ordering
    query = query.order_by(Team.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    teams = result.scalars().all()

    return [TeamResponse.model_validate(team) for team in teams]


@router.post("/teams", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
async def create_team(
    team_data: TeamCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN))
):
    """
    Create a new team in the organization (ADMIN only).
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not assigned to an organization"
        )

    # Check if team name already exists in this organization
    existing_team = await db.execute(
        select(Team).where(
            Team.organization_id == current_user.organization_id,
            Team.name == team_data.name
        )
    )
    if existing_team.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Team with name '{team_data.name}' already exists in this organization"
        )

    # Create team
    new_team = Team(
        organization_id=current_user.organization_id,
        **team_data.model_dump()
    )
    db.add(new_team)
    await db.commit()
    await db.refresh(new_team)

    return TeamResponse.model_validate(new_team)


@router.patch("/teams/{team_id}", response_model=TeamResponse)
async def update_team(
    team_id: int,
    team_data: TeamUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN))
):
    """
    Update team details (ADMIN only).
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not assigned to an organization"
        )

    result = await db.execute(
        select(Team).where(
            Team.id == team_id,
            Team.organization_id == current_user.organization_id
        )
    )
    team = result.scalar_one_or_none()

    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Team with ID {team_id} not found in your organization"
        )

    # Update fields
    update_data = team_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(team, field, value)

    await db.commit()
    await db.refresh(team)

    return TeamResponse.model_validate(team)


@router.delete("/teams/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_team(
    team_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN))
):
    """
    Delete a team (ADMIN only).

    Users in the team will have their team_id set to NULL.
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not assigned to an organization"
        )

    result = await db.execute(
        select(Team).where(
            Team.id == team_id,
            Team.organization_id == current_user.organization_id
        )
    )
    team = result.scalar_one_or_none()

    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Team with ID {team_id} not found in your organization"
        )

    # Set team_id to NULL for all users in this team
    users_in_team = await db.execute(
        select(User).where(User.team_id == team_id)
    )
    for user in users_in_team.scalars().all():
        user.team_id = None

    await db.delete(team)
    await db.commit()


# ==================== USER MANAGEMENT ====================

@router.get("/users", response_model=List[UserResponse])
async def list_organization_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = None,
    team_id: Optional[int] = None,
    role: Optional[UserRole] = None,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER))
):
    """
    List users in the organization (ADMIN or MANAGER).

    ADMIN: Can see all users in organization
    MANAGER: Can only see users in their team
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not assigned to an organization"
        )

    query = select(User).options(
        selectinload(User.team)
    ).where(User.organization_id == current_user.organization_id)

    # Apply RBAC - MANAGER can only see their team
    if current_user.role == UserRole.MANAGER:
        if not current_user.team_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Manager must be assigned to a team to view users"
            )
        query = query.where(User.team_id == current_user.team_id)

    # Apply filters
    if search:
        search_filter = or_(
            User.email.ilike(f"%{search}%"),
            User.first_name.ilike(f"%{search}%"),
            User.last_name.ilike(f"%{search}%")
        )
        query = query.where(search_filter)

    if team_id is not None:
        # MANAGER can only filter their own team
        if current_user.role == UserRole.MANAGER and team_id != current_user.team_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Managers can only view users in their own team"
            )
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


# ==================== INVITATION MANAGEMENT ====================

@router.post("/invitations", response_model=InvitationResponse, status_code=status.HTTP_201_CREATED)
async def send_invitation(
    invitation_data: InvitationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN))
):
    """
    Send an invitation to join the organization (ADMIN only).

    Creates invitation token and sends email to the invited user.
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not assigned to an organization"
        )

    # Validate team_id belongs to the organization if provided
    if invitation_data.team_id:
        team_result = await db.execute(
            select(Team).where(
                Team.id == invitation_data.team_id,
                Team.organization_id == current_user.organization_id
            )
        )
        if not team_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Team with ID {invitation_data.team_id} not found in your organization"
            )

    try:
        # Get frontend URL from settings or use default
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')

        invitation = await invitation_service.create_invitation(
            db=db,
            email=invitation_data.email,
            organization_id=current_user.organization_id,
            role=invitation_data.role,
            invited_by=current_user.id,
            team_id=invitation_data.team_id,
            frontend_url=frontend_url
        )

        return InvitationResponse.model_validate(invitation)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/invitations", response_model=List[InvitationResponse])
async def list_pending_invitations(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN))
):
    """
    List all pending invitations for the organization (ADMIN only).
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not assigned to an organization"
        )

    invitations = await invitation_service.get_pending_invitations(
        db=db,
        organization_id=current_user.organization_id
    )

    # Apply pagination manually (since service doesn't support it)
    paginated_invitations = invitations[skip:skip + limit]

    return [InvitationResponse.model_validate(inv) for inv in paginated_invitations]


@router.delete("/invitations/{invitation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_invitation(
    invitation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN))
):
    """
    Cancel a pending invitation (ADMIN only).
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not assigned to an organization"
        )

    try:
        success = await invitation_service.cancel_invitation(
            db=db,
            invitation_id=invitation_id,
            organization_id=current_user.organization_id
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Invitation with ID {invitation_id} not found"
            )

    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )


# ==================== PUBLIC INVITATION ENDPOINTS ====================

@router.get("/public/invitations/verify", response_model=InvitationVerify)
async def verify_invitation_token(
    token: str = Query(..., description="Invitation token"),
    db: AsyncSession = Depends(get_db)
):
    """
    Verify an invitation token (PUBLIC - no auth required).

    Returns invitation details if token is valid and not expired.
    """
    invitation_data = await invitation_service.verify_token(db=db, token=token)

    if not invitation_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or expired invitation token"
        )

    return InvitationVerify(**invitation_data)


@router.post("/public/invitations/accept", status_code=status.HTTP_200_OK)
async def accept_invitation(
    accept_data: InvitationAccept,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Accept an invitation and join the organization (AUTHENTICATED).

    User must be logged in and email must match the invitation.
    """
    try:
        success = await invitation_service.accept_invitation(
            db=db,
            token=accept_data.token,
            user_id=current_user.id
        )

        return {
            "message": "Invitation accepted successfully",
            "organization_id": current_user.organization_id,
            "team_id": current_user.team_id,
            "role": current_user.role
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
