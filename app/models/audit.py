"""
Audit logs and system settings
"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin


class AuditLog(Base, TimestampMixin):
    """
    Audit trail for all important actions
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Action details
    action = Column(String(100), nullable=False)  # create_session, update_score, etc.
    entity_type = Column(String(100), nullable=False)  # session, user, checklist, etc.
    entity_id = Column(Integer, nullable=True)

    # Changes (before/after as JSON)
    changes = Column(JSON, nullable=True)

    # Request metadata
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)

    # Relationships
    user = relationship("User", back_populates="audit_logs")


class Setting(Base, TimestampMixin):
    """
    System-wide settings (key-value store)
    """
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(255), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=True)
    description = Column(String(500), nullable=True)

    # Examples:
    # - risk_band_red_threshold: "60"
    # - risk_band_yellow_threshold: "80"
    # - default_scoring_mode: "equal_weight"
    # - email_from_name: "Sales Checklist Coach"
