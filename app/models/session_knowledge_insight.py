"""Cached session-level organization knowledge intelligence (Phase 3)."""
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base


class SessionKnowledgeInsight(Base):
    """Analysis snapshot for a deal session."""

    __tablename__ = "session_knowledge_insights"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(
        Integer,
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    next_best_answers = Column(JSONB, nullable=False, default=list)
    embedded_coaching = Column(JSONB, nullable=False, default=list)
    technical_risks = Column(JSONB, nullable=False, default=list)
    summary_text = Column(Text, nullable=True)
    has_technical_risk = Column(Boolean, nullable=False, default=False, index=True)
    knowledge_base_enabled = Column(Boolean, nullable=False, default=False)

    analyzed_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    session = relationship("Session", backref="knowledge_insight", uselist=False)
