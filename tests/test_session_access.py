from types import SimpleNamespace

from sqlalchemy import select
from sqlalchemy.dialects import postgresql

from app.api.dependencies import (
    get_session_access_filter,
    manager_can_view_owned_session,
    manager_visible_users_filter,
)
from app.models.session import Session
from app.models.user import UserRole


def _user(**kwargs):
    defaults = {
        "id": 13,
        "role": UserRole.MANAGER,
        "organization_id": 5,
        "team_id": None,
        "deleted_at": None,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _sql(clause) -> str:
    return str(
        select(Session.id)
        .where(clause)
        .compile(dialect=postgresql.dialect())
    )


def test_manager_without_team_scopes_to_organization():
    filt = get_session_access_filter(_user(team_id=None))
    sql = _sql(filt)
    assert "organization_id" in sql
    assert "sessions.user_id =" not in sql


def test_manager_with_team_includes_unassigned_same_org_users():
    sql = str(
        manager_visible_users_filter(_user(team_id=4)).compile(
            dialect=postgresql.dialect()
        )
    )
    assert "organization_id" in sql
    assert "team_id" in sql
    assert "IS NULL" in sql


def test_manager_can_view_unassigned_rep_session():
    manager = _user(team_id=4, organization_id=5)
    rep = _user(id=14, role=UserRole.REP, team_id=None, organization_id=5)
    assert manager_can_view_owned_session(manager, rep) is True


def test_manager_without_team_can_view_org_rep_session():
    manager = _user(team_id=None, organization_id=5)
    rep = _user(id=14, role=UserRole.REP, team_id=None, organization_id=5)
    assert manager_can_view_owned_session(manager, rep) is True


def test_manager_does_not_see_other_org():
    manager = _user(team_id=None, organization_id=5)
    rep = _user(id=99, role=UserRole.REP, team_id=None, organization_id=8)
    assert manager_can_view_owned_session(manager, rep) is False
