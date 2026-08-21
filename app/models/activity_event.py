"""
Activity events — first-party audit/activity stream for Super Admin (P2).
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.models.base import Base


class ActivityEvent(Base):
    """
    Append-only domain activity event.

    Events share a request-scoped `trace_id` so Super Admin can inspect a chain.
    """

    __tablename__ = "activity_events"
    __table_args__ = (
        Index("ix_activity_events_org_occurred", "organization_id", "occurred_at"),
        Index("ix_activity_events_trace_id", "trace_id"),
        Index("ix_activity_events_type_occurred", "event_type", "occurred_at"),
    )

    id = Column(String(36), primary_key=True)
    occurred_at = Column(DateTime, nullable=False, index=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    actor_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    event_type = Column(String(64), nullable=False, index=True)
    resource_type = Column(String(64), nullable=True)
    resource_id = Column(String(64), nullable=True)
    trace_id = Column(String(36), nullable=False)
    parent_event_id = Column(
        String(36),
        ForeignKey("activity_events.id", ondelete="SET NULL"),
        nullable=True,
    )
    payload = Column(JSONB, nullable=False, default=dict)
    ip_address = Column(String(64), nullable=True)
    user_agent = Column(Text, nullable=True)

    organization = relationship("Organization", backref="activity_events")
    actor = relationship("User", backref="activity_events", foreign_keys=[actor_user_id])
