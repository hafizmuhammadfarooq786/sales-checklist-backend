"""
Auth session registry — tracks JWT logins for Super Admin visibility (P1).
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.models.base import Base


class AuthSession(Base):
    """
    Server-side record of a JWT login session.

    id equals the JWT `jti` claim so sessions can be listed and revoked.
    """

    __tablename__ = "auth_sessions"

    id = Column(String(36), primary_key=True)  # UUID jti
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at = Column(DateTime, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    last_seen_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime, nullable=True, index=True)
    ip_address = Column(String(64), nullable=True)
    user_agent = Column(Text, nullable=True)
    remember_me = Column(Boolean, default=False, nullable=False)

    user = relationship("User", backref="auth_sessions")
    organization = relationship("Organization", backref="auth_sessions")

    @property
    def is_active(self) -> bool:
        from datetime import datetime

        now = datetime.utcnow()
        return self.revoked_at is None and self.expires_at > now
