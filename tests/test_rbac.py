"""
Role-Based Access Control (RBAC) Tests

Tests that verify proper access control for different user roles:
- REP: Can only access own sessions
- MANAGER: Can access sessions from users in their team
- ADMIN: Can access sessions from users in their organization
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.models.user import User, UserRole, Organization, Team
from app.models.session import Session, SessionStatus
from app.services.auth_service import auth_service


# ============================================================================
# Fixtures - Create multi-tenant test data
# ============================================================================

@pytest_asyncio.fixture
async def organization(db_session):
    """Create a test organization"""
    org = Organization(
        name="Test Organization",
        domain="test.com",
        is_active=True,
        scoring_mode="equal_weight",
        max_users=100
    )
    db_session.add(org)
    await db_session.commit()
    await db_session.refresh(org)
    return org


@pytest_asyncio.fixture
async def other_organization(db_session):
    """Create another organization for cross-org testing"""
    org = Organization(
        name="Other Organization",
        domain="other.com",
        is_active=True,
        scoring_mode="equal_weight",
        max_users=100
    )
    db_session.add(org)
    await db_session.commit()
    await db_session.refresh(org)
    return org


@pytest_asyncio.fixture
async def team(db_session, organization):
    """Create a team within the organization"""
    team = Team(
        organization_id=organization.id,
        name="Sales Team Alpha",
        description="Primary sales team",
        is_active=True
    )
    db_session.add(team)
    await db_session.commit()
    await db_session.refresh(team)
    return team


@pytest_asyncio.fixture
async def other_team(db_session, organization):
    """Create another team in same organization for cross-team testing"""
    team = Team(
        organization_id=organization.id,
        name="Sales Team Beta",
        description="Secondary sales team",
        is_active=True
    )
    db_session.add(team)
    await db_session.commit()
    await db_session.refresh(team)
    return team


@pytest_asyncio.fixture
async def rep_user(db_session, organization, team):
    """Create a REP user in team"""
    user = User(
        email="rep@test.com",
        password_hash=auth_service.hash_password("Test123!@#"),
        first_name="Rep",
        last_name="User",
        role=UserRole.REP,
        organization_id=organization.id,
        team_id=team.id,
        is_active=True,
        is_verified=True,
        failed_login_attempts=0
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def other_rep_user(db_session, organization, team):
    """Create another REP user in same team"""
    user = User(
        email="rep2@test.com",
        password_hash=auth_service.hash_password("Test123!@#"),
        first_name="Rep2",
        last_name="User",
        role=UserRole.REP,
        organization_id=organization.id,
        team_id=team.id,
        is_active=True,
        is_verified=True,
        failed_login_attempts=0
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def manager_user(db_session, organization, team):
    """Create a MANAGER user in team"""
    user = User(
        email="manager@test.com",
        password_hash=auth_service.hash_password("Test123!@#"),
        first_name="Manager",
        last_name="User",
        role=UserRole.MANAGER,
        organization_id=organization.id,
        team_id=team.id,
        is_active=True,
        is_verified=True,
        failed_login_attempts=0
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def other_team_manager(db_session, organization, other_team):
    """Create a MANAGER user in different team"""
    user = User(
        email="manager2@test.com",
        password_hash=auth_service.hash_password("Test123!@#"),
        first_name="Manager2",
        last_name="User",
        role=UserRole.MANAGER,
        organization_id=organization.id,
        team_id=other_team.id,
        is_active=True,
        is_verified=True,
        failed_login_attempts=0
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_user(db_session, organization):
    """Create an ADMIN user in organization (no specific team)"""
    user = User(
        email="admin@test.com",
        password_hash=auth_service.hash_password("Test123!@#"),
        first_name="Admin",
        last_name="User",
        role=UserRole.ADMIN,
        organization_id=organization.id,
        team_id=None,  # Admins typically don't belong to a specific team
        is_active=True,
        is_verified=True,
        failed_login_attempts=0
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def other_org_admin(db_session, other_organization):
    """Create an ADMIN user in different organization"""
    user = User(
        email="otheradmin@other.com",
        password_hash=auth_service.hash_password("Test123!@#"),
        first_name="OtherAdmin",
        last_name="User",
        role=UserRole.ADMIN,
        organization_id=other_organization.id,
        team_id=None,
        is_active=True,
        is_verified=True,
        failed_login_attempts=0
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


# Auth header fixtures
@pytest_asyncio.fixture
async def rep_headers(rep_user):
    """Auth headers for REP user"""
    token = auth_service.create_access_token({"sub": str(rep_user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def other_rep_headers(other_rep_user):
    """Auth headers for other REP user"""
    token = auth_service.create_access_token({"sub": str(other_rep_user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def manager_headers(manager_user):
    """Auth headers for MANAGER user"""
    token = auth_service.create_access_token({"sub": str(manager_user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def other_team_manager_headers(other_team_manager):
    """Auth headers for MANAGER in different team"""
    token = auth_service.create_access_token({"sub": str(other_team_manager.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def admin_headers(admin_user):
    """Auth headers for ADMIN user"""
    token = auth_service.create_access_token({"sub": str(admin_user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def other_org_admin_headers(other_org_admin):
    """Auth headers for ADMIN in different organization"""
    token = auth_service.create_access_token({"sub": str(other_org_admin.id)})
    return {"Authorization": f"Bearer {token}"}


# Session fixtures
@pytest_asyncio.fixture
async def rep_session(db_session, rep_user):
    """Create a session for REP user"""
    session = Session(
        user_id=rep_user.id,
        customer_name="Rep's Customer",
        opportunity_name="Rep's Opportunity",
        status=SessionStatus.COMPLETED
    )
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)
    return session


@pytest_asyncio.fixture
async def other_rep_session(db_session, other_rep_user):
    """Create a session for other REP user in same team"""
    session = Session(
        user_id=other_rep_user.id,
        customer_name="Other Rep's Customer",
        opportunity_name="Other Rep's Opportunity",
        status=SessionStatus.COMPLETED
    )
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)
    return session


@pytest_asyncio.fixture
async def other_team_session(db_session, other_team_manager):
    """Create a session for user in different team"""
    session = Session(
        user_id=other_team_manager.id,
        customer_name="Other Team Customer",
        opportunity_name="Other Team Opportunity",
        status=SessionStatus.COMPLETED
    )
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)
    return session


@pytest_asyncio.fixture
async def other_org_session(db_session, other_org_admin):
    """Create a session for user in different organization"""
    session = Session(
        user_id=other_org_admin.id,
        customer_name="Other Org Customer",
        opportunity_name="Other Org Opportunity",
        status=SessionStatus.COMPLETED
    )
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)
    return session


# ============================================================================
# REP Role Tests
# ============================================================================

@pytest.mark.asyncio
async def test_rep_can_list_own_sessions(
    client, rep_headers, rep_session
):
    """REP can see own sessions"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(
            "/api/v1/sessions/",
            headers=rep_headers
        )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["sessions"][0]["customer_name"] == "Rep's Customer"


@pytest.mark.asyncio
async def test_rep_cannot_list_other_rep_sessions(
    client, rep_headers, other_rep_session
):
    """REP cannot see sessions from other REPs in same team"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(
            "/api/v1/sessions/",
            headers=rep_headers
        )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0  # Should not see other rep's session


@pytest.mark.asyncio
async def test_rep_can_get_own_session(
    client, rep_headers, rep_session
):
    """REP can get own session details"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(
            f"/api/v1/sessions/{rep_session.id}",
            headers=rep_headers
        )

    assert response.status_code == 200
    data = response.json()
    assert data["customer_name"] == "Rep's Customer"


@pytest.mark.asyncio
async def test_rep_cannot_get_other_session(
    client, rep_headers, other_rep_session
):
    """REP cannot get session details from other users"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(
            f"/api/v1/sessions/{other_rep_session.id}",
            headers=rep_headers
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_rep_metrics_shows_only_own_sessions(
    client, rep_headers, rep_session, other_rep_session
):
    """REP metrics should only count own sessions"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(
            "/api/v1/users/me/metrics",
            headers=rep_headers
        )

    assert response.status_code == 200
    data = response.json()
    assert data["total_sessions"] == 1  # Only own session
    assert data["completed_sessions"] == 1


# ============================================================================
# MANAGER Role Tests
# ============================================================================

@pytest.mark.asyncio
async def test_manager_can_list_team_sessions(
    client, manager_headers, rep_session, other_rep_session
):
    """MANAGER can see all sessions from users in their team"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(
            "/api/v1/sessions/",
            headers=manager_headers
        )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2  # Both team members' sessions
    customer_names = [s["customer_name"] for s in data["sessions"]]
    assert "Rep's Customer" in customer_names
    assert "Other Rep's Customer" in customer_names


@pytest.mark.asyncio
async def test_manager_cannot_list_other_team_sessions(
    client, manager_headers, other_team_session
):
    """MANAGER cannot see sessions from other teams"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(
            "/api/v1/sessions/",
            headers=manager_headers
        )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0  # Should not see other team's sessions


@pytest.mark.asyncio
async def test_manager_can_get_team_member_session(
    client, manager_headers, rep_session
):
    """MANAGER can get session details from team members"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(
            f"/api/v1/sessions/{rep_session.id}",
            headers=manager_headers
        )

    assert response.status_code == 200
    data = response.json()
    assert data["customer_name"] == "Rep's Customer"


@pytest.mark.asyncio
async def test_manager_cannot_get_other_team_session(
    client, manager_headers, other_team_session
):
    """MANAGER cannot get session details from other teams"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(
            f"/api/v1/sessions/{other_team_session.id}",
            headers=manager_headers
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_manager_metrics_shows_team_sessions(
    client, manager_headers, rep_session, other_rep_session, other_team_session
):
    """MANAGER metrics should count all team sessions"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(
            "/api/v1/users/me/metrics",
            headers=manager_headers
        )

    assert response.status_code == 200
    data = response.json()
    assert data["total_sessions"] == 2  # Both team members
    assert data["completed_sessions"] == 2


# ============================================================================
# ADMIN Role Tests
# ============================================================================

@pytest.mark.asyncio
async def test_admin_can_list_all_org_sessions(
    client, admin_headers, rep_session, other_rep_session, other_team_session
):
    """ADMIN can see all sessions from users in their organization"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(
            "/api/v1/sessions/",
            headers=admin_headers
        )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3  # All sessions in organization
    customer_names = [s["customer_name"] for s in data["sessions"]]
    assert "Rep's Customer" in customer_names
    assert "Other Rep's Customer" in customer_names
    assert "Other Team Customer" in customer_names


@pytest.mark.asyncio
async def test_admin_cannot_list_other_org_sessions(
    client, admin_headers, other_org_session
):
    """ADMIN cannot see sessions from other organizations"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(
            "/api/v1/sessions/",
            headers=admin_headers
        )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0  # Should not see other org's sessions


@pytest.mark.asyncio
async def test_admin_can_get_any_org_session(
    client, admin_headers, rep_session, other_team_session
):
    """ADMIN can get session details from any user in organization"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response1 = await ac.get(
            f"/api/v1/sessions/{rep_session.id}",
            headers=admin_headers
        )
        response2 = await ac.get(
            f"/api/v1/sessions/{other_team_session.id}",
            headers=admin_headers
        )

    assert response1.status_code == 200
    assert response2.status_code == 200
    assert response1.json()["customer_name"] == "Rep's Customer"
    assert response2.json()["customer_name"] == "Other Team Customer"


@pytest.mark.asyncio
async def test_admin_cannot_get_other_org_session(
    client, admin_headers, other_org_session
):
    """ADMIN cannot get session details from other organizations"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(
            f"/api/v1/sessions/{other_org_session.id}",
            headers=admin_headers
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_admin_metrics_shows_org_sessions(
    client, admin_headers, rep_session, other_rep_session, other_team_session, other_org_session
):
    """ADMIN metrics should count all organization sessions"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(
            "/api/v1/users/me/metrics",
            headers=admin_headers
        )

    assert response.status_code == 200
    data = response.json()
    assert data["total_sessions"] == 3  # All org sessions, not other org
    assert data["completed_sessions"] == 3


# ============================================================================
# Cross-Organization Tests
# ============================================================================

@pytest.mark.asyncio
async def test_different_org_admins_cannot_see_each_other_sessions(
    client, admin_headers, other_org_admin_headers, rep_session, other_org_session
):
    """Admins from different organizations cannot see each other's sessions"""
    # Admin from org1 should only see org1 sessions
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response1 = await ac.get(
            "/api/v1/sessions/",
            headers=admin_headers
        )

    # Admin from org2 should only see org2 sessions
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response2 = await ac.get(
            "/api/v1/sessions/",
            headers=other_org_admin_headers
        )

    assert response1.status_code == 200
    assert response2.status_code == 200

    data1 = response1.json()
    data2 = response2.json()

    assert data1["total"] == 1  # Only org1 session
    assert data2["total"] == 1  # Only org2 session

    assert data1["sessions"][0]["customer_name"] == "Rep's Customer"
    assert data2["sessions"][0]["customer_name"] == "Other Org Customer"
