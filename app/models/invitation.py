"""
Invitation Model
Handles user invitations to organizations and teams
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin


class Invitation(Base, TimestampMixin):
    """
    User invitation model for organization/team onboarding.

    Invitations are sent via email with a secure token.
    Users can accept the invitation to join the organization and team.
    """
    __tablename__ = "invitations"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=True)
    role = Column(String(50), nullable=False)  # rep, manager, admin
    token = Column(String(255), unique=True, nullable=False, index=True)
    invited_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    expires_at = Column(DateTime, nullable=False)
    accepted_at = Column(DateTime, nullable=True)

    # Relationships
    organization = relationship("Organization", backref="invitations")
    team = relationship("Team", backref="invitations")
    inviter = relationship("User", foreign_keys=[invited_by])

    @property
    def is_expired(self) -> bool:
        """Check if invitation has expired"""
        return datetime.utcnow() > self.expires_at

    @property
    def is_accepted(self) -> bool:
        """Check if invitation has been accepted"""
        return self.accepted_at is not None

    @property
    def is_valid(self) -> bool:
        """Check if invitation is still valid (not expired and not accepted)"""
        return not self.is_expired and not self.is_accepted

    def __repr__(self):
        return f"<Invitation(id={self.id}, email='{self.email}', org_id={self.organization_id}, valid={self.is_valid})>"
