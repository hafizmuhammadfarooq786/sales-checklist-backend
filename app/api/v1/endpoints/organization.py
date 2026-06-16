"""
Organization API Endpoints - ADMIN level
Handles organization settings, teams, invitations, and user management
"""
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func
from sqlalchemy.orm import selectinload
from typing import List, Optional

from app.db.session import get_db
from app.models import Organization, User, Team, OrganizationSettings
from app.models.user import UserRole
from app.schemas.organization import (
    OrganizationResponse,
    OrganizationSettingsUpdate,
    OrganizationSettingsResponse,
    OrganizationProfileResponse,
    OrganizationProfileUpdate,
    ExecutiveSponsorResponse,
    UserRoleSummary,
    INDUSTRY_OPTIONS,
    TeamCreate,
    TeamUpdate,
    TeamResponse,
)
from app.schemas.invitation import (
    InvitationCreate,
    InvitationResponse,
    InvitationVerify,
    InvitationAccept,
    InvitationResendResponse,
    InvitationsBulkResendResponse,
)
from app.schemas.user import UserResponse
from app.api.dependencies import require_roles, get_current_invitation_user
from app.services.invitation_service import (
    get_invitation_service,
    exclude_users_with_pending_invitations,
)
from app.services.s3_service import get_s3_service
from app.services.org_logo_service import (
    guess_logo_content_type,
    load_organization_logo_bytes,
)
from app.core.config import settings

router = APIRouter()
invitation_service = get_invitation_service()

_LOGO_MAX_BYTES = 2 * 1024 * 1024
_LOGO_ALLOWED_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


async def _get_org_settings(db: AsyncSession, organization_id: int) -> OrganizationSettings:
    result = await db.execute(
        select(OrganizationSettings).where(
            OrganizationSettings.organization_id == organization_id
        )
    )
    org_settings = result.scalar_one_or_none()
    if not org_settings:
        org_settings = OrganizationSettings(
            organization_id=organization_id,
            allow_self_registration=False,
            default_role="rep",
            settings={},
        )
        db.add(org_settings)
        await db.commit()
        await db.refresh(org_settings)
    return org_settings


def _executive_sponsor_from_user(user: User) -> ExecutiveSponsorResponse:
    """Executive sponsor is the organization administrator (logged-in admin)."""
    name = f"{user.first_name or ''} {user.last_name or ''}".strip() or user.email
    return ExecutiveSponsorResponse(
        user_id=user.id,
        name=name,
        email=user.email,
        direct_dial=user.direct_dial,
        cell_phone=user.cell_phone,
        role="Administrator",
    )


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


@router.get("/profile", response_model=OrganizationProfileResponse)
async def get_organization_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    """Combined company profile for org admin form."""
    if not current_user.organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User is not assigned to an organization")

    org_result = await db.execute(
        select(Organization).where(Organization.id == current_user.organization_id)
    )
    organization = org_result.scalar_one_or_none()
    if not organization:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    org_settings = await _get_org_settings(db, current_user.organization_id)
    return OrganizationProfileResponse(
        organization=OrganizationResponse.model_validate(organization),
        settings=OrganizationSettingsResponse.model_validate(org_settings),
        executive_sponsor=_executive_sponsor_from_user(current_user),
    )


@router.patch("/profile", response_model=OrganizationProfileResponse)
async def update_organization_profile(
    profile_data: OrganizationProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    """Update company name, industry, executive sponsor, and registration settings."""
    if not current_user.organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User is not assigned to an organization")

    org_result = await db.execute(
        select(Organization).where(Organization.id == current_user.organization_id)
    )
    organization = org_result.scalar_one_or_none()
    if not organization:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    org_settings = await _get_org_settings(db, current_user.organization_id)
    update_data = profile_data.model_dump(exclude_unset=True)

    org_fields = {}
    if "name" in update_data:
        org_fields["name"] = update_data.pop("name")
    if "industry" in update_data:
        org_fields["industry"] = update_data.pop("industry")
    for field, value in org_fields.items():
        setattr(organization, field, value)

    sponsor_fields = ("direct_dial", "cell_phone")
    for field in sponsor_fields:
        if field not in update_data:
            continue
        value = update_data.pop(field)
        if value is None:
            continue
        current_value = getattr(current_user, field)
        if (current_value or "").strip():
            continue
        setattr(current_user, field, value)

    for field, value in update_data.items():
        setattr(org_settings, field, value)

    await db.commit()
    await db.refresh(organization)
    await db.refresh(org_settings)
    await db.refresh(current_user)

    return OrganizationProfileResponse(
        organization=OrganizationResponse.model_validate(organization),
        settings=OrganizationSettingsResponse.model_validate(org_settings),
        executive_sponsor=_executive_sponsor_from_user(current_user),
    )


@router.get("/industries", response_model=List[str])
async def list_industry_options(
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    """Industry dropdown options for company profile."""
    del current_user
    return INDUSTRY_OPTIONS


@router.post("/logo", response_model=OrganizationSettingsResponse)
async def upload_organization_logo(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    """Upload company logo image and persist URL on organization settings."""
    if not current_user.organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User is not assigned to an organization")

    content_type = (file.content_type or "").lower()
    if content_type not in _LOGO_ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Logo must be PNG, JPEG, WEBP, or GIF",
        )

    file_bytes = await file.read()
    if not file_bytes or len(file_bytes) < 32:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid logo file")
    if len(file_bytes) > _LOGO_MAX_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Logo must be 2MB or smaller")

    ext = _LOGO_ALLOWED_TYPES[content_type]
    org_id = current_user.organization_id
    s3_key = f"branding/{org_id}/logo-{uuid.uuid4().hex}{ext}"
    logo_url: str

    try:
        s3_service = get_s3_service()
        logo_url = await s3_service.upload_bytes(
            file_bytes,
            s3_key,
            content_type=content_type,
        )
    except Exception:
        logo_url = f"uploads/branding/{org_id}/logo{ext}"
        local_path = Path(logo_url)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(file_bytes)

    org_settings = await _get_org_settings(db, org_id)
    org_settings.logo_url = logo_url
    await db.commit()
    await db.refresh(org_settings)
    return OrganizationSettingsResponse.model_validate(org_settings)


@router.get("/logo")
async def get_organization_logo(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    """Return the organization logo image bytes for preview and download."""
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not assigned to an organization",
        )

    org_settings = await _get_org_settings(db, current_user.organization_id)
    if not org_settings.logo_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No logo configured",
        )

    logo_bytes = await load_organization_logo_bytes(org_settings.logo_url)
    if not logo_bytes:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Logo file not found",
        )

    return Response(
        content=logo_bytes,
        media_type=guess_logo_content_type(org_settings.logo_url),
        headers={"Cache-Control": "private, max-age=300"},
    )


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
        org_settings = await _get_org_settings(db, current_user.organization_id)

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

    # Create team (Team model has no description column; exclude from dump)
    new_team = Team(
        organization_id=current_user.organization_id,
        **team_data.model_dump(exclude={"description"})
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

    # Update fields (Team model has no description column; exclude it)
    update_data = team_data.model_dump(exclude_unset=True, exclude={"description"})
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
    ).where(
        User.organization_id == current_user.organization_id,
        User.deleted_at.is_(None),  # Exclude soft-deleted users
        User.is_verified.is_(True),  # Only show accepted (verified) members
        exclude_users_with_pending_invitations(
            current_user.organization_id, User.email
        ),
        # Org admin (executive sponsor) is not a team member — managers and reps only
        User.role.in_([UserRole.MANAGER, UserRole.REP]),
    )

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


@router.get("/users/summary", response_model=UserRoleSummary)
async def get_organization_user_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    """Role counts for org admin user summary cards."""
    if not current_user.organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User is not assigned to an organization")

    base_filter = (
        User.organization_id == current_user.organization_id,
        User.deleted_at.is_(None),
        User.is_verified.is_(True),
        exclude_users_with_pending_invitations(
            current_user.organization_id, User.email
        ),
    )

    async def _count(role: UserRole) -> int:
        result = await db.execute(
            select(func.count()).select_from(User).where(*base_filter, User.role == role)
        )
        return int(result.scalar() or 0)

    executives = await _count(UserRole.EXECUTIVE)
    managers = await _count(UserRole.MANAGER)
    salespeople = await _count(UserRole.REP)
    administrators = await _count(UserRole.ADMIN)
    # Team members only (excludes org admin / executive sponsor)
    total = managers + salespeople

    return UserRoleSummary(
        executives=executives,
        managers=managers,
        salespeople=salespeople,
        administrators=administrators,
        total_users=total,
    )


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
            frontend_url=frontend_url,
            first_name=invitation_data.first_name,
            last_name=invitation_data.last_name,
            job_title=invitation_data.job_title,
            direct_dial=invitation_data.direct_dial,
            cell_phone=invitation_data.cell_phone,
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
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post(
    "/invitations/{invitation_id}/resend",
    response_model=InvitationResendResponse,
)
async def resend_invitation(
    invitation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    """Resend a pending invitation with a new link and temporary password (ADMIN only)."""
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not assigned to an organization",
        )

    frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:3000")
    try:
        invitation = await invitation_service.resend_invitation(
            db=db,
            invitation_id=invitation_id,
            organization_id=current_user.organization_id,
            frontend_url=frontend_url,
        )
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return InvitationResendResponse(
        message=f"Invitation email resent to {invitation.email}",
        invitation=InvitationResponse.model_validate(invitation),
    )


@router.post(
    "/invitations/resend-all",
    response_model=InvitationsBulkResendResponse,
)
async def resend_all_invitations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    """Resend all pending invitation emails for the organization (ADMIN only)."""
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not assigned to an organization",
        )

    frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:3000")
    try:
        count = await invitation_service.resend_pending_invitations_for_organization(
            db=db,
            organization_id=current_user.organization_id,
            frontend_url=frontend_url,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    if count == 0:
        return InvitationsBulkResendResponse(
            message="No pending invitations to resend",
            invitations_resent=0,
        )

    return InvitationsBulkResendResponse(
        message=f"{count} invitation email(s) resent",
        invitations_resent=count,
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
    current_user: User = Depends(get_current_invitation_user)
):
    """
    Accept an invitation and join the organization (AUTHENTICATED).

    User must be logged in and email must match the invitation.
    """
    try:
        await invitation_service.accept_invitation(
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
