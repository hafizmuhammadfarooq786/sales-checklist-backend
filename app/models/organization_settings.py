"""
Organization Settings Model
Stores configuration and preferences for each organization
"""
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin
from app.models.organization_knowledge import KnowledgeBaseStatus


class OrganizationSettings(Base, TimestampMixin):
    """
    Organization settings and configuration.

    Stores preferences, branding, and feature flags for each organization.
    """
    __tablename__ = "organization_settings"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)

    # Registration settings
    allow_self_registration = Column(Boolean, default=False, nullable=False)
    default_role = Column(String(50), default="rep", nullable=False)

    # Branding
    logo_url = Column(Text, nullable=True)
    primary_color = Column(String(7), nullable=True)  # Hex color code

    # Executive sponsor (client onboarding form)
    executive_sponsor_name = Column(String(255), nullable=True)
    executive_sponsor_email = Column(String(255), nullable=True)
    executive_sponsor_direct_dial = Column(String(50), nullable=True)
    executive_sponsor_cell_phone = Column(String(50), nullable=True)

    # Organization Knowledge Intelligence
    knowledge_base_status = Column(
        SQLEnum(
            KnowledgeBaseStatus,
            name="knowledgebasestatus",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=KnowledgeBaseStatus.NOT_STARTED,
    )
    knowledge_base_ready_at = Column(DateTime(timezone=True), nullable=True)
    knowledge_base_error_message = Column(Text, nullable=True)

    # Flexible settings storage (JSONB)
    settings = Column(JSONB, nullable=True, default={})

    # Relationships
    organization = relationship("Organization", backref="settings", uselist=False)

    def __repr__(self):
        return f"<OrganizationSettings(org_id={self.organization_id}, allow_self_reg={self.allow_self_registration})>"
