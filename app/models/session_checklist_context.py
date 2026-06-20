"""Per-session deal context for checklist items (Organization Knowledge Intelligence)."""
from sqlalchemy import Column, Integer, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin


class SessionChecklistItemContext(Base, TimestampMixin):
    """Optional deal-specific context a rep enters for a checklist item."""

    __tablename__ = "session_checklist_item_contexts"
    __table_args__ = (
        UniqueConstraint(
            "session_id",
            "checklist_item_id",
            name="uq_session_checklist_item_context",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(
        Integer,
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    checklist_item_id = Column(
        Integer,
        ForeignKey("checklist_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    deal_context = Column(Text, nullable=True)

    session = relationship("Session", backref="checklist_item_contexts")
    checklist_item = relationship("ChecklistItem", backref="session_contexts")
