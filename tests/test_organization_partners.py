"""Which organizations a checklist may be shared with.

Sharing has always been confined to the owning organization. National accounts
need several companies on one checklist, so an explicit partner row widens it —
and nothing else should. These guard both halves of that: partners are included,
and an unrelated organization still is not.
"""
import asyncio

import pytest

from app.api.v1.endpoints.session_shares import _shareable_organization_ids
from app.models.organization_partner import ordered_pair


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _FakeDb:
    """Returns the partner rows a real query would, and records the call."""

    def __init__(self, rows):
        self._rows = rows
        self.executed = 0

    async def execute(self, _stmt):
        self.executed += 1
        return _FakeResult(self._rows)


def _shareable(owner_org_id, rows):
    return asyncio.run(_shareable_organization_ids(owner_org_id, _FakeDb(rows)))


def test_no_partners_means_own_organization_only():
    """The default for every existing customer: unchanged isolation."""
    assert _shareable(5, []) == [5]


def test_partner_listed_as_b_is_included():
    assert _shareable(5, [(5, 9)]) == [5, 9]


def test_partner_listed_as_a_is_included():
    """Pairs are stored lower id first, so the owner can be on either side."""
    assert _shareable(9, [(5, 9)]) == [5, 9]


def test_several_partners_are_all_included():
    """David confirmed 2-4 organizations on a national account."""
    assert _shareable(5, [(5, 9), (3, 5), (5, 11)]) == [3, 5, 9, 11]


def test_owner_appears_once_even_if_partnered_twice():
    assert _shareable(5, [(5, 9), (5, 9)]) == [5, 9]


@pytest.mark.parametrize(
    "owner, rows, intruder",
    [
        (5, [], 7),
        (5, [(5, 9)], 7),
        (5, [(5, 9), (3, 5)], 12),
    ],
)
def test_unrelated_organization_is_never_shareable(owner, rows, intruder):
    """The property that matters: a partner row must not open the whole system.

    Without this, a manager at one customer could share a checklist with users
    at a company they have no relationship with.
    """
    assert intruder not in _shareable(owner, rows)


def test_ordered_pair_is_symmetric():
    """Stored lower id first so a pair exists once, whichever way it is created."""
    assert ordered_pair(9, 5) == (5, 9)
    assert ordered_pair(5, 9) == (5, 9)
    assert ordered_pair(5, 9) == ordered_pair(9, 5)
