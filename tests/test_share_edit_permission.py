"""Write access granted by an "edit" share, and withheld by a "read" one.

A partner contributing to a shared checklist is the only case where someone
changes a session their organization does not own, so these guard the exact
boundary: edit shares get through, read shares do not, and nothing else moves.
"""
from types import SimpleNamespace

from sqlalchemy import select
from sqlalchemy.dialects import postgresql

from app.api.dependencies import (
    get_owned_session_filter,
    get_session_access_filter,
    get_session_write_filter,
)
from app.models.session import Session
from app.models.user import UserRole


def _user(**kwargs):
    defaults = {
        "id": 13,
        "role": UserRole.REP,
        "organization_id": 5,
        "team_id": None,
        "deleted_at": None,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _sql(clause) -> str:
    return str(
        select(Session.id).where(clause).compile(dialect=postgresql.dialect())
    )


def test_write_filter_consults_session_shares():
    """Before this change it never looked at shares at all."""
    sql = _sql(get_session_write_filter(_user()))
    assert "session_shares" in sql


def test_write_filter_requires_the_edit_permission():
    """A read share must not grant writes, so the permission is in the SQL."""
    sql = _sql(get_session_write_filter(_user()))
    assert "permission" in sql


def test_read_access_ignores_the_permission_column():
    """Any share grants read; only writes care which kind it is."""
    sql = _sql(get_session_access_filter(_user()))
    assert "session_shares" in sql
    assert "permission" not in sql


def test_owned_filter_excludes_shares_entirely():
    """Dashboard metrics count your own pipeline.

    A checklist shared from a partner company belongs to them; counting it
    here would overstate the numbers on both sides.
    """
    sql = _sql(get_owned_session_filter(_user()))
    assert "session_shares" not in sql


def test_system_admin_write_does_not_depend_on_shares():
    """A system admin already reaches everything; adding a share term would
    only widen a filter that is already total."""
    sql = _sql(get_session_write_filter(_user(role=UserRole.SYSTEM_ADMIN)))
    assert "session_shares" not in sql


def test_owner_still_reaches_their_own_sessions():
    """The share term is an addition, not a replacement."""
    sql = _sql(get_session_write_filter(_user(id=77)))
    assert "sessions.user_id" in sql
