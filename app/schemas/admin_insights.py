"""
Admin insights schemas — Super Admin org adoption / usage views (P0).
"""
from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from app.schemas.organization import OrganizationResponse


ActivationStatus = Literal["never_logged_in", "invited_only", "active"]


class OrganizationAdoptionStats(BaseModel):
    has_any_login: bool = False
    first_login_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None
    last_activity_at: Optional[datetime] = None
    users_total: int = 0
    users_invited: int = 0
    users_accepted: int = 0
    users_never_logged_in: int = 0
    teams_total: int = 0
    teams_active: int = 0
    deal_sessions_total: int = 0
    deal_sessions_last_30d: int = 0
    activation_status: ActivationStatus = "never_logged_in"


class OrganizationInsightsLive(BaseModel):
    """Placeholder until P1 auth_sessions; always zeros in P0."""
    active_auth_sessions: int = 0
    active_users_now: int = 0


class OrganizationInsightsResponse(BaseModel):
    organization: OrganizationResponse
    approved_at: Optional[datetime] = None
    adoption: OrganizationAdoptionStats
    live: OrganizationInsightsLive = Field(default_factory=OrganizationInsightsLive)


class OrganizationWithUsageResponse(OrganizationResponse):
    """Org list row with usage summary for Super Admin."""
    users_total: int = 0
    users_never_logged_in: int = 0
    last_login_at: Optional[datetime] = None
    teams_active: int = 0
    deal_sessions_total: int = 0
    deal_sessions_last_30d: int = 0
    activation_status: ActivationStatus = "never_logged_in"


class PlatformInsightsOverview(BaseModel):
    total_organizations: int = 0
    active_organizations: int = 0
    never_logged_in_organizations: int = 0
    invited_only_organizations: int = 0
    active_usage_organizations: int = 0
    total_users: int = 0
    users_never_logged_in: int = 0
    total_teams: int = 0
    deal_sessions_total: int = 0
    deal_sessions_last_30d: int = 0
    organizations: List[OrganizationWithUsageResponse] = Field(default_factory=list)
