"""
Platform-wide transactional email templates edited by SYSTEM_ADMIN.
"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin


class EmailTemplate(Base, TimestampMixin):
    """Stored HTML + subject for a named transactional email."""

    __tablename__ = "email_templates"

    slug = Column(String(64), primary_key=True)
    name = Column(String(120), nullable=False)
    description = Column(Text, nullable=True)
    subject = Column(String(500), nullable=False)
    html_body = Column(Text, nullable=False)
    updated_by_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    updated_by = relationship("User", foreign_keys=[updated_by_user_id])

    def __repr__(self) -> str:
        return f"<EmailTemplate(slug={self.slug})>"
