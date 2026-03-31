"""
Opportunity-scoped checklist item notes (versioned).
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin


class ChecklistItemNote(Base, TimestampMixin):
    """
    One row per version of a note for (checklist_item_id, opportunity_key).
    Exactly one row per (checklist_item_id, opportunity_key) has is_active = True.
    """

    __tablename__ = "checklist_item_notes"

    id = Column(Integer, primary_key=True, index=True)
    checklist_item_id = Column(
        Integer, ForeignKey("checklist_items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    session_id = Column(
        Integer, ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    customer_name = Column(String(255), nullable=False)
    opportunity_name = Column(String(255), nullable=False)
    opportunity_key = Column(String(64), nullable=False, index=True)

    note_text = Column(Text, nullable=True)
    decision_influencers = Column(JSONB, nullable=True)
    structured_content = Column(JSONB, nullable=True)

    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)
    version = Column(Integer, nullable=False)
    previous_version_id = Column(
        Integer, ForeignKey("checklist_item_notes.id", ondelete="SET NULL"), nullable=True
    )

    created_by_user = relationship("User", foreign_keys=[created_by_user_id])
    updated_by_user = relationship("User", foreign_keys=[updated_by_user_id])
    checklist_item = relationship(
        "ChecklistItem", back_populates="item_notes", foreign_keys=[checklist_item_id]
    )
    session = relationship("Session", foreign_keys=[session_id])
