"""An approved collaboration between two organizations.

National accounts are worked by several companies at once — a distributor and
its partners on the same opportunity — so a checklist has to be shareable
outside the organization that created it.

Opening sharing to every organization would let a manager at one client reach
users at an unrelated one, so the pairing is explicit: a checklist can only be
shared outside its own organization when a row here links the two.

Pairs are symmetric. `a_id` is always the lower id so the pair appears once and
the unique constraint can enforce it; use `ordered_pair()` rather than writing
the ids directly.
"""
from sqlalchemy import Boolean, CheckConstraint, Column, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin


class OrganizationPartner(Base, TimestampMixin):
    __tablename__ = "organization_partners"
    __table_args__ = (
        UniqueConstraint("a_id", "b_id", name="uq_organization_partners_pair"),
        # Guards the ordering the helper relies on, and stops an organization
        # being partnered with itself.
        CheckConstraint("a_id < b_id", name="ck_organization_partners_ordered"),
    )

    id = Column(Integer, primary_key=True, index=True)
    a_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    b_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    is_active = Column(Boolean, nullable=False, default=True)
    created_by_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    a = relationship("Organization", foreign_keys=[a_id])
    b = relationship("Organization", foreign_keys=[b_id])
    created_by = relationship("User", foreign_keys=[created_by_user_id])


def ordered_pair(org_id: int, other_org_id: int) -> tuple[int, int]:
    """The (a_id, b_id) for a pair, lower id first."""
    return (org_id, other_org_id) if org_id < other_org_id else (other_org_id, org_id)
