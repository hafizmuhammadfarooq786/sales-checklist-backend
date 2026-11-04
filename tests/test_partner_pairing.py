"""Pairing rules behind the partner admin screens.

The endpoints store a pair once, lower id first, so adding A→B and B→A cannot
produce two rows that later disagree about whether a partnership exists.
"""
import pytest

from app.models.organization_partner import ordered_pair


@pytest.mark.parametrize(
    "a, b",
    [(5, 9), (9, 5), (1, 2), (2, 1), (100, 3), (3, 100)],
)
def test_pair_is_stored_lower_id_first(a, b):
    assert ordered_pair(a, b) == (min(a, b), max(a, b))


@pytest.mark.parametrize("a, b", [(5, 9), (12, 4), (2, 77)])
def test_adding_either_direction_yields_the_same_row(a, b):
    """Admin at A adding B must collide with admin at B adding A.

    Without this the unique constraint would not catch the duplicate and both
    organizations would see a partner the other could remove independently.
    """
    assert ordered_pair(a, b) == ordered_pair(b, a)


def test_self_pairing_violates_the_ordering_the_check_constraint_enforces():
    """ck_organization_partners_ordered requires a_id < b_id.

    ordered_pair(5, 5) gives (5, 5), which the database rejects — the endpoint
    returns 400 before reaching it, and this records why the constraint exists.
    """
    a_id, b_id = ordered_pair(5, 5)
    assert not (a_id < b_id)


def test_response_carries_the_link_id_and_the_organization_id_separately():
    """The UI removes a partnership by link id, not organization id.

    If the response exposed only one number, a client would send the wrong one
    to DELETE /partners/{id} and remove an unrelated partnership that happened
    to share that value.
    """
    from app.api.v1.endpoints.organization import PartnerOrganizationResponse

    fields = PartnerOrganizationResponse.model_fields
    assert "id" in fields
    assert "organization_id" in fields
