"""Read-only access granted so another salesperson can view a session."""
from sqlalchemy import Column, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin


class SessionShare(Base, TimestampMixin):
    """
    A manager adds a salesperson from the same organization to a session.

    permission is read. The added salesperson can open the checklist and
    results, and cannot change them.
    """

    __tablename__ = "session_shares"
    __table_args__ = (
        UniqueConstraint("session_id", "user_id", name="uq_session_shares_session_user"),
    )

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(
        Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    permission = Column(String(16), nullable=False, default="read")
    added_by_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    user = relationship("User", foreign_keys=[user_id])
    added_by = relationship("User", foreign_keys=[added_by_user_id])
