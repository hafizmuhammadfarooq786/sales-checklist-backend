"""
Manager Notes Model - Coaching feedback from managers on sessions
"""
from sqlalchemy import Column, Integer, Text, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin


class ManagerNote(Base, TimestampMixin):
    """
    Manager notes/coaching feedback on sessions

    - Managers (or Admins) can leave coaching notes on any session they can view
    - Reps can view notes left on their own sessions
    - Notes are editable by the manager who wrote them
    - Multiple notes can be added to a session (conversation/thread style)
    """
    __tablename__ = "manager_notes"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    manager_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Note content
    note_text = Column(Text, nullable=False)
    is_edited = Column(Boolean, default=False, nullable=False)  # Track if note was edited

    # Relationships
    session = relationship("Session", back_populates="manager_notes")
    manager = relationship("User", foreign_keys=[manager_id])  # Manager who wrote the note

    def __repr__(self):
        return f"<ManagerNote(id={self.id}, session_id={self.session_id}, manager_id={self.manager_id})>"
