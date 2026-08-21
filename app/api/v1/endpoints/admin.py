"""
Admin API Endpoints - SYSTEM_ADMIN only
Handles organization and user management across all organizations
"""
import secrets
import base64
from fastapi import APIRouter, Depends, HTTPException, status, Query, Header
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, delete
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import datetime
from sqlalchemy.exc import IntegrityError

from app.db.session import get_db
from app.models import Organization, User, Team, OrganizationSettings
from app.models.invitation import Invitation
from app.models.organization_registration import (
    OrganizationRegistrationRequest,
    RegistrationStatus,
)
from app.models.user import UserRole
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationUpdate,
    OrganizationResponse,
)
from app.schemas.admin_insights import (
    OrganizationInsightsResponse,
    OrganizationWithUsageResponse,
    PlatformInsightsOverview,
)
from app.schemas.auth_session import AuthSessionResponse
from app.schemas.activity_event import (
    ActivityEventResponse,
    ActivityEventListResponse,
    ActivityEventDetailResponse,
    ActivityTraceResponse,
)
from app.schemas.organization_registration import (
    OrganizationRegistrationApproveResponse,
    OrganizationRegistrationReject,
    OrganizationRegistrationResponse,
    OrganizationRegistrationResendInvitationsResponse,
    SignupUserRowResponse,
)
from app.schemas.user import UserResponse, UserUpdate, AdminUserProvision
from app.api.dependencies import require_roles
from app.services.admin_insights_service import get_admin_insights_service
from app.services.auth_service import auth_service
from app.services.auth_session_service import auth_session_service
from app.services.activity_emitter import activity_emitter
from app.services import activity_event_types as evt
from app.services.invitation_service import get_invitation_service
from app.services.org_logo_service import guess_logo_content_type, load_organization_logo_bytes
from app.services.registration_service import get_registration_service
from app.core.config import settings

router = APIRouter()


def _require_internal_admin_api_key(x_internal_api_key: str = Header(..., alias="X-Internal-Api-Key")) -> None:
    """Require a shared key for direct SYSTEM_ADMIN provisioning APIs."""
    if not settings.INTERNAL_ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Internal admin API key is not configured"
        )

    if not secrets.compare_digest(x_internal_api_key, settings.INTERNAL_ADMIN_API_KEY):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid internal admin API key"
        )


# ==================== INSIGHTS (P0) ====================

@router.get("/insights/overview", response_model=PlatformInsightsOverview)
async def get_platform_insights_overview(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SYSTEM_ADMIN)),
):
    """Platform-wide adoption overview across all organizations (SYSTEM_ADMIN only)."""
    service = get_admin_insights_service(db)
    return await service.get_platform_overview()


# ==================== ORGANIZATIONS ====================

@router.get("/organizations", response_model=List[OrganizationWithUsageResponse])
async def list_organizations(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SYSTEM_ADMIN))
):
    """
    List all organizations with usage summary (SYSTEM_ADMIN only).

    Supports pagination and filtering by:
    - search: Search by organization name
    - is_active: Filter by active status
    """
    service = get_admin_insights_service(db)
    return await service.list_organizations_with_usage(
        skip=skip,
        limit=limit,
        search=search,
        is_active=is_active,
    )


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


@router.get(
    "/organizations/{org_id}/insights",
    response_model=OrganizationInsightsResponse,
)
async def get_organization_insights(
    org_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SYSTEM_ADMIN)),
):
    """
    Company adoption insights after registration approval (SYSTEM_ADMIN only).

    Answers: have they logged in, invites accepted, teams, deal sessions,
    and live auth-session counts from the auth_sessions registry (P1).
    """
    service = get_admin_insights_service(db)
    try:
        return await service.get_organization_insights(org_id)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


def _auth_session_to_response(session) -> AuthSessionResponse:
    user = getattr(session, "user", None)
    name = None
    if user:
        name = f"{user.first_name or ''} {user.last_name or ''}".strip() or None
    return AuthSessionResponse(
        id=session.id,
        user_id=session.user_id,
        organization_id=session.organization_id,
        user_email=user.email if user else None,
        user_name=name,
        created_at=session.created_at,
        expires_at=session.expires_at,
        last_seen_at=session.last_seen_at,
        revoked_at=session.revoked_at,
        ip_address=session.ip_address,
        user_agent=session.user_agent,
        remember_me=bool(session.remember_me),
        is_active=session.is_active,
    )


@router.get(
    "/organizations/{org_id}/auth-sessions",
    response_model=List[AuthSessionResponse],
)
async def list_organization_auth_sessions(
    org_id: int,
    status_filter: str = Query("active", alias="status", regex="^(active|all)$"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SYSTEM_ADMIN)),
):
    """List login sessions for an organization (SYSTEM_ADMIN only)."""
    org = await db.execute(select(Organization).where(Organization.id == org_id))
    if not org.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization with ID {org_id} not found",
        )

    sessions = await auth_session_service.list_sessions(
        db,
        organization_id=org_id,
        active_only=(status_filter == "active"),
        skip=skip,
        limit=limit,
    )
    return [_auth_session_to_response(s) for s in sessions]


@router.get(
    "/users/{user_id}/auth-sessions",
    response_model=List[AuthSessionResponse],
)
async def list_user_auth_sessions(
    user_id: int,
    status_filter: str = Query("active", alias="status", regex="^(active|all)$"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SYSTEM_ADMIN)),
):
    """List login sessions for a user (SYSTEM_ADMIN only)."""
    result = await db.execute(
        select(User).where(User.id == user_id, User.deleted_at.is_(None))
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found",
        )

    sessions = await auth_session_service.list_sessions(
        db,
        user_id=user_id,
        active_only=(status_filter == "active"),
        skip=skip,
        limit=limit,
    )
    return [_auth_session_to_response(s) for s in sessions]


@router.post(
    "/auth-sessions/{session_id}/revoke",
    response_model=AuthSessionResponse,
)
async def revoke_auth_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SYSTEM_ADMIN)),
):
    """Force-revoke a login session (SYSTEM_ADMIN only)."""
    session = await auth_session_service.revoke_session(
        db, session_id, actor_user_id=current_user.id
    )
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Auth session not found",
        )
    # Re-fetch with user relationship for response enrichment
    session = await auth_session_service.get_session(db, session_id) or session
    await activity_emitter.emit(
        db,
        event_type=evt.ADMIN_AUTH_SESSION_REVOKED,
        organization_id=session.organization_id,
        actor_user_id=current_user.id,
        resource_type="auth_session",
        resource_id=session_id,
        payload={"target_user_id": session.user_id},
        commit=True,
    )
    return _auth_session_to_response(session)


def _activity_event_to_response(event) -> ActivityEventResponse:
    actor = getattr(event, "actor", None)
    org = getattr(event, "organization", None)
    name = None
    if actor:
        name = f"{actor.first_name or ''} {actor.last_name or ''}".strip() or None
    return ActivityEventResponse(
        id=event.id,
        occurred_at=event.occurred_at,
        organization_id=event.organization_id,
        organization_name=org.name if org else None,
        actor_user_id=event.actor_user_id,
        actor_email=actor.email if actor else None,
        actor_name=name,
        event_type=event.event_type,
        resource_type=event.resource_type,
        resource_id=event.resource_id,
        trace_id=event.trace_id,
        parent_event_id=event.parent_event_id,
        payload=event.payload or {},
        ip_address=event.ip_address,
        user_agent=event.user_agent,
    )


def _parse_event_cursor(cursor: Optional[str]) -> tuple[Optional[datetime], Optional[str]]:
    if not cursor:
        return None, None
    try:
        occurred_raw, event_id = cursor.split("|", 1)
        return datetime.fromisoformat(occurred_raw), event_id
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid cursor format",
        )


@router.get(
    "/organizations/{org_id}/events",
    response_model=ActivityEventListResponse,
)
async def list_organization_events(
    org_id: int,
    event_type: Optional[str] = None,
    event_prefix: Optional[str] = Query(
        None, regex="^(auth|invite|org|session|admin)\\.?$"
    ),
    from_dt: Optional[datetime] = Query(None, alias="from"),
    to_dt: Optional[datetime] = Query(None, alias="to"),
    cursor: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SYSTEM_ADMIN)),
):
    """Paginated activity feed for an organization (SYSTEM_ADMIN only)."""
    org = await db.execute(select(Organization).where(Organization.id == org_id))
    if not org.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization with ID {org_id} not found",
        )

    cursor_occurred_at, cursor_id = _parse_event_cursor(cursor)
    prefix = event_prefix.rstrip(".") + "." if event_prefix else None
    events = await activity_emitter.list_for_organization(
        db,
        organization_id=org_id,
        event_type=event_type,
        event_type_prefix=prefix,
        from_dt=from_dt,
        to_dt=to_dt,
        limit=limit + 1,
        cursor_occurred_at=cursor_occurred_at,
        cursor_id=cursor_id,
    )
    next_cursor = None
    if len(events) > limit:
        last = events[limit - 1]
        next_cursor = f"{last.occurred_at.isoformat()}|{last.id}"
        events = events[:limit]

    return ActivityEventListResponse(
        items=[_activity_event_to_response(e) for e in events],
        next_cursor=next_cursor,
    )


@router.get("/events/recent", response_model=ActivityEventListResponse)
async def list_recent_platform_events(
    event_prefix: Optional[str] = Query(
        None, regex="^(auth|invite|org|session|admin)\\.?$"
    ),
    limit: int = Query(40, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SYSTEM_ADMIN)),
):
    """Recent cross-org activity for Platform Insights (SYSTEM_ADMIN only)."""
    prefix = event_prefix.rstrip(".") + "." if event_prefix else None
    events = await activity_emitter.list_recent(
        db,
        event_type_prefix=prefix,
        limit=limit,
    )
    return ActivityEventListResponse(
        items=[_activity_event_to_response(e) for e in events],
        next_cursor=None,
    )


@router.get("/events/{event_id}", response_model=ActivityEventDetailResponse)
async def get_activity_event(
    event_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SYSTEM_ADMIN)),
):
    """Event detail including siblings that share the same trace_id."""
    event = await activity_emitter.get_event(db, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    related = await activity_emitter.list_trace(db, event.trace_id)
    base = _activity_event_to_response(event)
    return ActivityEventDetailResponse(
        **base.model_dump(),
        related_events=[_activity_event_to_response(e) for e in related],
    )


@router.get("/traces/{trace_id}", response_model=ActivityTraceResponse)
async def get_activity_trace(
    trace_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SYSTEM_ADMIN)),
):
    """Ordered event chain for a trace_id (SYSTEM_ADMIN only)."""
    events = await activity_emitter.list_trace(db, trace_id)
    if not events:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trace not found")
    return ActivityTraceResponse(
        trace_id=trace_id,
        events=[_activity_event_to_response(e) for e in events],
    )


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

    WARNING: This will cascade delete teams/settings/invitations and related org data.
    Non-deleted users must be removed first.
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

    # Block while any non-deleted users still belong to the org
    user_count_result = await db.execute(
        select(func.count(User.id)).where(
            User.organization_id == org_id,
            User.deleted_at.is_(None),
        )
    )
    user_count = user_count_result.scalar() or 0

    if user_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete organization with {user_count} active users. Remove users first."
        )

    try:
        # Use SQL DELETE so PostgreSQL ON DELETE CASCADE runs.
        # session.delete(org) loads invitation relationships and tries to SET NULL
        # on invitations.organization_id (NOT NULL) → IntegrityError / 500.
        await db.execute(
            delete(Invitation).where(Invitation.organization_id == org_id)
        )
        await db.execute(
            delete(Organization).where(Organization.id == org_id)
        )
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Cannot delete organization because related records still reference it. "
                "Remove users and dependent data first."
            ),
        ) from exc


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
    include_deleted: bool = Query(False, description="Include soft-deleted users"),
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
    - include_deleted: Include soft-deleted users (default: false)
    """
    query = select(User).options(
        selectinload(User.organization),
        selectinload(User.team)
    )

    # Exclude soft-deleted users by default
    if not include_deleted:
        query = query.where(User.deleted_at.is_(None))

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
    include_deleted: bool = Query(False, description="Include soft-deleted user"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SYSTEM_ADMIN))
):
    """
    Get user details by ID (SYSTEM_ADMIN only).
    """
    query = select(User).options(
        selectinload(User.organization),
        selectinload(User.team)
    ).where(User.id == user_id)

    # Exclude soft-deleted users by default
    if not include_deleted:
        query = query.where(User.deleted_at.is_(None))

    result = await db.execute(query)
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


@router.post("/users/provision", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def provision_user(
    user_data: AdminUserProvision,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SYSTEM_ADMIN)),
    _: None = Depends(_require_internal_admin_api_key),
):
    """
    Provision a user directly via SYSTEM_ADMIN API key-gated endpoint.
    """
    org_result = await db.execute(
        select(Organization).where(Organization.id == user_data.organization_id)
    )
    organization = org_result.scalar_one_or_none()
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization with ID {user_data.organization_id} not found"
        )

    if user_data.team_id is not None:
        team_result = await db.execute(
            select(Team).where(
                Team.id == user_data.team_id,
                Team.organization_id == user_data.organization_id
            )
        )
        if not team_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Team does not belong to the provided organization"
            )

    existing_user_result = await db.execute(
        select(User).where(User.email == user_data.email)
    )
    if existing_user_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    user = User(
        email=user_data.email,
        password_hash=auth_service.hash_password(user_data.password),
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        role=user_data.role,
        organization_id=user_data.organization_id,
        team_id=user_data.team_id,
        is_active=user_data.is_active,
        is_verified=user_data.is_verified,
        must_change_password=user_data.must_change_password,
    )
    db.add(user)
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
    Hard delete a user (SYSTEM_ADMIN only).

    This permanently removes the user record.
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

    # Hard delete: permanently remove user row.
    await db.delete(user)
    await db.commit()


@router.post("/users/{user_id}/restore", response_model=UserResponse)
async def restore_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SYSTEM_ADMIN))
):
    """
    Restore a soft-deleted user (SYSTEM_ADMIN only).

    This reactivates a previously deleted user, allowing them to log in again.
    All their historical data (sessions, scores, etc.) remains intact.
    """
    result = await db.execute(
        select(User)
        .options(selectinload(User.organization), selectinload(User.team))
        .where(
            User.id == user_id,
            User.deleted_at.is_not(None)  # Only get deleted users
        )
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deleted user with ID {user_id} not found"
        )

    # Restore the user
    user.deleted_at = None
    user.deleted_by = None
    user.is_active = True  # Reactivate the user

    await db.commit()
    await db.refresh(user)

    return UserResponse.model_validate(user)


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
        select(func.count(Organization.id)).where(Organization.is_active.is_(True))
    )
    active_orgs = active_org_count_result.scalar() or 0

    # Count users
    user_count_result = await db.execute(select(func.count(User.id)))
    total_users = user_count_result.scalar() or 0

    active_user_count_result = await db.execute(
        select(func.count(User.id)).where(User.is_active.is_(True))
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


# ==================== ORGANIZATION REGISTRATIONS ====================


async def _registration_logo_preview(
    request: OrganizationRegistrationRequest,
) -> tuple[Optional[str], Optional[str]]:
    if not request.logo_url:
        return None, None
    logo_bytes = await load_organization_logo_bytes(request.logo_url)
    if not logo_bytes:
        return None, None
    return (
        base64.b64encode(logo_bytes).decode("ascii"),
        guess_logo_content_type(request.logo_url),
    )


def _registration_to_response(
    request: OrganizationRegistrationRequest,
    *,
    logo_preview_base64: Optional[str] = None,
    logo_content_type: Optional[str] = None,
) -> OrganizationRegistrationResponse:
    additional_users = [
        SignupUserRowResponse.model_validate(row)
        for row in (request.additional_users or [])
    ]
    return OrganizationRegistrationResponse(
        id=request.id,
        status=request.status,
        company_name=request.company_name,
        industry=request.industry,
        logo_url=request.logo_url,
        logo_preview_base64=logo_preview_base64,
        logo_content_type=logo_content_type,
        admin_first_name=request.admin_first_name,
        admin_last_name=request.admin_last_name,
        admin_email=request.admin_email,
        admin_direct_dial=request.admin_direct_dial,
        admin_cell_phone=request.admin_cell_phone,
        additional_users=additional_users,
        organization_id=request.organization_id,
        reviewed_by=request.reviewed_by,
        reviewed_at=request.reviewed_at,
        rejection_reason=request.rejection_reason,
        created_at=request.created_at,
        updated_at=request.updated_at,
    )


@router.get("/registrations", response_model=List[OrganizationRegistrationResponse])
async def list_organization_registrations(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    status: Optional[RegistrationStatus] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SYSTEM_ADMIN)),
):
    """List public organization registration requests (SYSTEM_ADMIN only)."""
    query = select(OrganizationRegistrationRequest)

    if status is not None:
        query = query.where(OrganizationRegistrationRequest.status == status)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(
            or_(
                OrganizationRegistrationRequest.company_name.ilike(pattern),
                OrganizationRegistrationRequest.admin_email.ilike(pattern),
            )
        )

    query = (
        query.order_by(OrganizationRegistrationRequest.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    requests = result.scalars().all()
    return [_registration_to_response(item) for item in requests]


@router.get("/registrations/{request_id}", response_model=OrganizationRegistrationResponse)
async def get_organization_registration(
    request_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SYSTEM_ADMIN)),
):
    """Get a single organization registration request."""
    registration_service = get_registration_service()
    try:
        request = await registration_service._get_request(db, request_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    logo_preview_base64, logo_content_type = await _registration_logo_preview(request)
    return _registration_to_response(
        request,
        logo_preview_base64=logo_preview_base64,
        logo_content_type=logo_content_type,
    )


@router.get("/registrations/{request_id}/logo")
async def get_registration_logo(
    request_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SYSTEM_ADMIN)),
):
    """Return logo bytes for a pending registration request."""
    registration_service = get_registration_service()
    try:
        request = await registration_service._get_request(db, request_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    if not request.logo_url:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No logo uploaded")

    logo_bytes = await load_organization_logo_bytes(request.logo_url)
    if not logo_bytes:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Logo file not found")

    return Response(
        content=logo_bytes,
        media_type=guess_logo_content_type(request.logo_url),
    )


@router.post(
    "/registrations/{request_id}/approve",
    response_model=OrganizationRegistrationApproveResponse,
)
async def approve_organization_registration(
    request_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SYSTEM_ADMIN)),
):
    """Approve a pending registration: create org, settings, and send invites."""
    registration_service = get_registration_service()
    try:
        request, organization_id, invitations_sent = await registration_service.approve_registration(
            db,
            request_id,
            current_user,
            frontend_url=settings.FRONTEND_URL,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return OrganizationRegistrationApproveResponse(
        registration=_registration_to_response(request),
        organization_id=organization_id,
        invitations_sent=invitations_sent,
        message=(
            f"Approved {request.company_name}. "
            f"Organization admin credentials emailed."
            + (
                f" {invitations_sent} team invitation email(s) sent."
                if invitations_sent
                else ""
            )
        ),
    )


@router.post(
    "/registrations/{request_id}/resend-invitations",
    response_model=OrganizationRegistrationResendInvitationsResponse,
)
async def resend_registration_invitations(
    request_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SYSTEM_ADMIN)),
):
    """Resend pending invitation emails for an approved registration's organization."""
    registration_service = get_registration_service()
    try:
        request = await registration_service._get_request(db, request_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    if request.status != RegistrationStatus.APPROVED or not request.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitations can only be resent for approved registrations",
        )

    invitation_service = get_invitation_service()
    try:
        count = await invitation_service.resend_pending_invitations_for_organization(
            db=db,
            organization_id=request.organization_id,
            frontend_url=settings.FRONTEND_URL,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    if count == 0:
        return OrganizationRegistrationResendInvitationsResponse(
            invitations_resent=0,
            message="No pending invitations to resend for this organization",
        )

    return OrganizationRegistrationResendInvitationsResponse(
        invitations_resent=count,
        message=f"{count} invitation email(s) resent for {request.company_name}",
    )


@router.post(
    "/registrations/{request_id}/reject",
    response_model=OrganizationRegistrationResponse,
)
async def reject_organization_registration(
    request_id: int,
    payload: OrganizationRegistrationReject,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SYSTEM_ADMIN)),
):
    """Reject a pending registration request."""
    registration_service = get_registration_service()
    try:
        request = await registration_service.reject_registration(
            db,
            request_id,
            current_user,
            reason=payload.reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _registration_to_response(request)
