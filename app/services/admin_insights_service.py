"""
Admin insights service — aggregate org adoption from existing tables (P0).
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Sequence

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Organization, Team, User
from app.models.activity_event import ActivityEvent
from app.models.auth_session import AuthSession
from app.models.invitation import Invitation
from app.models.organization_registration import (
    OrganizationRegistrationRequest,
    RegistrationStatus,
)
from app.models.session import Session
from app.models.user import UserRole
from app.schemas.admin_insights import (
    ActivationStatus,
    OrganizationAdoptionStats,
    OrganizationInsightsLive,
    OrganizationInsightsResponse,
    OrganizationWithUsageResponse,
    PlatformInsightsOverview,
)
from app.schemas.organization import OrganizationResponse
from app.services.auth_session_service import auth_session_service


def _activation_status(
    *,
    has_any_login: bool,
    users_invited: int,
    users_accepted: int,
) -> ActivationStatus:
    if has_any_login:
        return "active"
    if users_invited > 0 or users_accepted > 0:
        return "invited_only"
    return "never_logged_in"


class AdminInsightsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_platform_overview(self) -> PlatformInsightsOverview:
        orgs_result = await self.db.execute(
            select(Organization).order_by(Organization.created_at.desc())
        )
        orgs = list(orgs_result.scalars().all())
        usage_by_id = await self._usage_for_org_ids([o.id for o in orgs])

        with_usage = [
            self._to_org_with_usage(org, usage_by_id.get(org.id))
            for org in orgs
        ]

        never_logged_in = sum(1 for row in with_usage if row.activation_status == "never_logged_in")
        invited_only = sum(1 for row in with_usage if row.activation_status == "invited_only")
        active_usage = sum(1 for row in with_usage if row.activation_status == "active")

        user_totals = await self.db.execute(
            select(
                func.count(User.id),
                func.count(User.id).filter(
                    and_(User.last_login.is_(None), User.deleted_at.is_(None))
                ),
            ).where(
                User.deleted_at.is_(None),
                User.role != UserRole.SYSTEM_ADMIN,
            )
        )
        total_users, users_never = user_totals.one()

        teams_total = (
            await self.db.execute(select(func.count(Team.id)))
        ).scalar() or 0

        since = datetime.utcnow() - timedelta(days=30)
        session_totals = await self.db.execute(
            select(
                func.count(Session.id),
                func.count(Session.id).filter(Session.created_at >= since),
            ).select_from(Session).join(User, User.id == Session.user_id).where(
                User.deleted_at.is_(None),
                User.role != UserRole.SYSTEM_ADMIN,
            )
        )
        deal_total, deal_30d = session_totals.one()

        active_sessions, active_users = await auth_session_service.count_active(self.db)

        return PlatformInsightsOverview(
            total_organizations=len(orgs),
            active_organizations=sum(1 for o in orgs if o.is_active),
            never_logged_in_organizations=never_logged_in,
            invited_only_organizations=invited_only,
            active_usage_organizations=active_usage,
            total_users=int(total_users or 0),
            users_never_logged_in=int(users_never or 0),
            total_teams=int(teams_total),
            deal_sessions_total=int(deal_total or 0),
            deal_sessions_last_30d=int(deal_30d or 0),
            active_auth_sessions=active_sessions,
            active_users_now=active_users,
            organizations=with_usage,
        )

    async def list_organizations_with_usage(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> List[OrganizationWithUsageResponse]:
        query = select(Organization)
        if search:
            query = query.where(Organization.name.ilike(f"%{search.strip()}%"))
        if is_active is not None:
            query = query.where(Organization.is_active.is_(is_active))
        query = query.order_by(Organization.created_at.desc()).offset(skip).limit(limit)

        result = await self.db.execute(query)
        orgs = list(result.scalars().all())
        usage_by_id = await self._usage_for_org_ids([o.id for o in orgs])
        return [self._to_org_with_usage(org, usage_by_id.get(org.id)) for org in orgs]

    async def get_organization_insights(self, org_id: int) -> OrganizationInsightsResponse:
        result = await self.db.execute(
            select(Organization).where(Organization.id == org_id)
        )
        org = result.scalar_one_or_none()
        if not org:
            raise LookupError(f"Organization with ID {org_id} not found")

        usage = (await self._usage_for_org_ids([org_id])).get(org_id) or {}
        approved_at = await self._approved_at(org_id)

        adoption = OrganizationAdoptionStats(
            has_any_login=bool(usage.get("has_any_login")),
            first_login_at=usage.get("first_login_at"),
            last_login_at=usage.get("last_login_at"),
            last_activity_at=usage.get("last_activity_at"),
            users_total=int(usage.get("users_total") or 0),
            users_invited=int(usage.get("users_invited") or 0),
            users_accepted=int(usage.get("users_accepted") or 0),
            users_never_logged_in=int(usage.get("users_never_logged_in") or 0),
            teams_total=int(usage.get("teams_total") or 0),
            teams_active=int(usage.get("teams_active") or 0),
            deal_sessions_total=int(usage.get("deal_sessions_total") or 0),
            deal_sessions_last_30d=int(usage.get("deal_sessions_last_30d") or 0),
            activation_status=usage.get("activation_status") or "never_logged_in",
        )

        active_sessions, active_users = await auth_session_service.count_active(
            self.db, organization_id=org_id
        )

        return OrganizationInsightsResponse(
            organization=OrganizationResponse.model_validate(org),
            approved_at=approved_at,
            adoption=adoption,
            live=OrganizationInsightsLive(
                active_auth_sessions=active_sessions,
                active_users_now=active_users,
            ),
        )

    async def _approved_at(self, org_id: int) -> Optional[datetime]:
        result = await self.db.execute(
            select(OrganizationRegistrationRequest.reviewed_at)
            .where(
                OrganizationRegistrationRequest.organization_id == org_id,
                OrganizationRegistrationRequest.status == RegistrationStatus.APPROVED,
            )
            .order_by(OrganizationRegistrationRequest.reviewed_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _usage_for_org_ids(
        self, org_ids: Sequence[int]
    ) -> Dict[int, Dict]:
        if not org_ids:
            return {}

        since = datetime.utcnow() - timedelta(days=30)
        ids = list(org_ids)

        user_rows = await self.db.execute(
            select(
                User.organization_id,
                func.count(User.id).label("users_total"),
                func.count(User.id).filter(User.last_login.is_(None)).label("users_never"),
                func.min(User.last_login).label("first_login"),
                func.max(User.last_login).label("last_login"),
            )
            .where(
                User.organization_id.in_(ids),
                User.deleted_at.is_(None),
            )
            .group_by(User.organization_id)
        )
        user_map = {
            row.organization_id: row for row in user_rows.all() if row.organization_id is not None
        }

        invite_rows = await self.db.execute(
            select(
                Invitation.organization_id,
                func.count(Invitation.id).label("invited"),
                func.count(Invitation.id).filter(Invitation.accepted_at.is_not(None)).label("accepted"),
            )
            .where(Invitation.organization_id.in_(ids))
            .group_by(Invitation.organization_id)
        )
        invite_map = {row.organization_id: row for row in invite_rows.all()}

        team_rows = await self.db.execute(
            select(
                Team.organization_id,
                func.count(Team.id).label("teams_total"),
                func.count(Team.id).filter(Team.is_active.is_(True)).label("teams_active"),
            )
            .where(Team.organization_id.in_(ids))
            .group_by(Team.organization_id)
        )
        team_map = {row.organization_id: row for row in team_rows.all()}

        session_rows = await self.db.execute(
            select(
                User.organization_id,
                func.count(Session.id).label("sessions_total"),
                func.count(Session.id).filter(Session.created_at >= since).label("sessions_30d"),
                func.max(Session.created_at).label("last_session_at"),
            )
            .select_from(Session)
            .join(User, User.id == Session.user_id)
            .where(
                User.organization_id.in_(ids),
                User.deleted_at.is_(None),
            )
            .group_by(User.organization_id)
        )
        session_map = {
            row.organization_id: row for row in session_rows.all() if row.organization_id is not None
        }

        now = datetime.utcnow()
        auth_rows = await self.db.execute(
            select(
                AuthSession.organization_id,
                func.count(AuthSession.id).label("active_auth_sessions"),
            )
            .where(
                AuthSession.organization_id.in_(ids),
                AuthSession.revoked_at.is_(None),
                AuthSession.expires_at > now,
            )
            .group_by(AuthSession.organization_id)
        )
        auth_map = {
            row.organization_id: int(row.active_auth_sessions)
            for row in auth_rows.all()
            if row.organization_id is not None
        }

        event_rows = await self.db.execute(
            select(
                ActivityEvent.organization_id,
                func.max(ActivityEvent.occurred_at).label("last_event_at"),
            )
            .where(ActivityEvent.organization_id.in_(ids))
            .group_by(ActivityEvent.organization_id)
        )
        event_map = {
            row.organization_id: row.last_event_at
            for row in event_rows.all()
            if row.organization_id is not None
        }

        out: Dict[int, Dict] = {}
        for org_id in ids:
            u = user_map.get(org_id)
            inv = invite_map.get(org_id)
            t = team_map.get(org_id)
            s = session_map.get(org_id)

            users_total = int(u.users_total) if u else 0
            users_never = int(u.users_never) if u else 0
            first_login = u.first_login if u else None
            last_login = u.last_login if u else None
            users_invited = int(inv.invited) if inv else 0
            users_accepted = int(inv.accepted) if inv else 0
            last_session = s.last_session_at if s else None
            last_event = event_map.get(org_id)

            last_activity_candidates = [
                d for d in (last_login, last_session, last_event) if d is not None
            ]
            last_activity_at = max(last_activity_candidates) if last_activity_candidates else None
            has_any_login = last_login is not None

            out[org_id] = {
                "has_any_login": has_any_login,
                "first_login_at": first_login,
                "last_login_at": last_login,
                "last_activity_at": last_activity_at,
                "users_total": users_total,
                "users_invited": users_invited,
                "users_accepted": users_accepted,
                "users_never_logged_in": users_never,
                "teams_total": int(t.teams_total) if t else 0,
                "teams_active": int(t.teams_active) if t else 0,
                "deal_sessions_total": int(s.sessions_total) if s else 0,
                "deal_sessions_last_30d": int(s.sessions_30d) if s else 0,
                "active_auth_sessions": auth_map.get(org_id, 0),
                "activation_status": _activation_status(
                    has_any_login=has_any_login,
                    users_invited=users_invited,
                    users_accepted=users_accepted,
                ),
            }
        return out

    def _to_org_with_usage(
        self, org: Organization, usage: Optional[Dict]
    ) -> OrganizationWithUsageResponse:
        usage = usage or {}
        base = OrganizationResponse.model_validate(org)
        return OrganizationWithUsageResponse(
            **base.model_dump(),
            users_total=int(usage.get("users_total") or 0),
            users_never_logged_in=int(usage.get("users_never_logged_in") or 0),
            last_login_at=usage.get("last_login_at"),
            teams_active=int(usage.get("teams_active") or 0),
            deal_sessions_total=int(usage.get("deal_sessions_total") or 0),
            deal_sessions_last_30d=int(usage.get("deal_sessions_last_30d") or 0),
            activation_status=usage.get("activation_status") or "never_logged_in",
            active_auth_sessions=int(usage.get("active_auth_sessions") or 0),
        )


def get_admin_insights_service(db: AsyncSession) -> AdminInsightsService:
    return AdminInsightsService(db)
