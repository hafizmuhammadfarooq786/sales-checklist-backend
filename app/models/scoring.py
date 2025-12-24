"""
Scoring and Coaching Feedback models
"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, Float, JSON, Enum as SQLEnum, DateTime
from sqlalchemy.orm import relationship
import enum

from app.models.base import Base, TimestampMixin


class RiskBand(str, enum.Enum):
    """Risk assessment bands"""
    GREEN = "green"  # Healthy: 80+
    YELLOW = "yellow"  # Caution: 60-79
    RED = "red"  # At risk: < 60


class ScoringResult(Base, TimestampMixin):
    """
    Calculated scores for a session
    """
    __tablename__ = "scoring_results"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, unique=True)

    # Overall score
    total_score = Column(Float, nullable=False)  # 0-100
    risk_band = Column(SQLEnum(RiskBand), nullable=False)

    # Per-category scores (stored as JSON for flexibility)
    # Example: {"Trigger Event": 85, "Priority": 70, ...}
    category_scores = Column(JSON, nullable=True)

    # Strengths and Gaps
    top_strengths = Column(JSON, nullable=True)  # Top 3 strongest categories
    top_gaps = Column(JSON, nullable=True)  # Bottom 3 weakest categories

    # Metadata
    items_validated = Column(Integer, nullable=False, default=0)  # Count of items with True
    items_total = Column(Integer, nullable=False, default=92)

    # Relationships
    session = relationship("Session", back_populates="scoring_result")


class ScoreHistory(Base, TimestampMixin):
    """
    Historical record of score calculations for a session.
    Preserves score changes when users edit AI answers and recalculate.
    """
    __tablename__ = "score_history"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    scoring_result_id = Column(Integer, ForeignKey("scoring_results.id", ondelete="SET NULL"), nullable=True, index=True)

    # Score snapshot
    total_score = Column(Float, nullable=False)  # 0-100
    risk_band = Column(SQLEnum(RiskBand), nullable=False)
    items_validated = Column(Integer, nullable=False)
    items_total = Column(Integer, nullable=False)

    # Change tracking
    calculated_at = Column(DateTime, nullable=False)
    score_change = Column(Float, nullable=True)  # Difference from previous score
    trigger_event = Column(String(100), nullable=True)  # What caused the recalculation

    # Audit trail
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    session = relationship("Session", back_populates="score_history")
    scoring_result = relationship("ScoringResult")


class CoachingFeedback(Base, TimestampMixin):
    """
    AI-generated personalized coaching feedback
    """
    __tablename__ = "coaching_feedback"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, unique=True)

    # Text feedback (200-300 words)
    feedback_text = Column(Text, nullable=False)

    # Structured coaching points
    strengths = Column(JSON, nullable=True)  # List of strengths with explanations
    improvement_areas = Column(JSON, nullable=True)  # List of areas to work on
    action_items = Column(JSON, nullable=True)  # Specific recommended actions

    # Audio coaching (TTS from ElevenLabs)
    audio_s3_bucket = Column(String(255), nullable=True)
    audio_s3_key = Column(String(500), nullable=True)
    audio_duration = Column(Integer, nullable=True)  # Seconds

    # Generation metadata
    generated_at = Column(DateTime, nullable=True)
    openai_request_id = Column(String(255), nullable=True)

    # Relationships
    session = relationship("Session", back_populates="coaching_feedback")
