"""
Session models - Sales call recording and analysis
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, Float, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum

from app.models.base import Base, TimestampMixin


class SessionStatus(str, enum.Enum):
    """Session processing status"""
    DRAFT = "draft"  # Started but not submitted
    UPLOADING = "uploading"  # Audio file uploading
    PROCESSING = "processing"  # Transcribing audio
    ANALYZING = "analyzing"  # AI mapping to checklist
    SCORING = "scoring"  # Calculating scores
    COMPLETED = "completed"  # All done
    FAILED = "failed"  # Error occurred


class Session(Base, TimestampMixin):
    """
    Sales call session - main entity
    """
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Customer/Opportunity details
    customer_name = Column(String(255), nullable=False)
    opportunity_name = Column(String(255), nullable=True)
    decision_influencer = Column(String(255), nullable=True)
    deal_stage = Column(String(100), nullable=True)

    # Status
    status = Column(SQLEnum(SessionStatus), default=SessionStatus.DRAFT, nullable=False)

    # Timestamps for tracking
    submitted_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Offline sync
    is_synced = Column(Boolean, default=True)  # False if created offline
    sync_attempted_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="sessions")
    audio_file = relationship("AudioFile", back_populates="session", uselist=False, cascade="all, delete-orphan")
    transcript = relationship("Transcript", back_populates="session", uselist=False, cascade="all, delete-orphan")
    responses = relationship("SessionResponse", back_populates="session", cascade="all, delete-orphan")
    scoring_result = relationship("ScoringResult", back_populates="session", uselist=False, cascade="all, delete-orphan")
    coaching_feedback = relationship("CoachingFeedback", back_populates="session", uselist=False, cascade="all, delete-orphan")
    report = relationship("Report", back_populates="session", uselist=False, cascade="all, delete-orphan")


class AudioFile(Base, TimestampMixin):
    """
    Audio recording metadata
    """
    __tablename__ = "audio_files"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, unique=True)

    # File details
    filename = Column(String(500), nullable=False)
    file_path = Column(String(1000), nullable=False)  # S3 URL or local path
    storage_type = Column(String(50), default="local")  # 's3' or 'local'
    file_size = Column(Integer, nullable=False)  # Bytes
    duration_seconds = Column(Float, nullable=True)  # Audio duration in seconds
    mime_type = Column(String(100), nullable=False)

    # Relationships
    session = relationship("Session", back_populates="audio_file")


class Transcript(Base, TimestampMixin):
    """
    OpenAI Whisper transcription result
    """
    __tablename__ = "transcripts"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, unique=True)

    # Transcription
    text = Column(Text, nullable=False)
    language = Column(String(10), nullable=True)  # Detected language (e.g., "en")

    # Metadata from Whisper
    duration = Column(Float, nullable=True)  # Audio duration in seconds
    words_count = Column(Integer, nullable=True)

    # Processing
    transcribed_at = Column(DateTime, nullable=True)
    processing_time = Column(Float, nullable=True)  # Seconds

    # OpenAI request ID for debugging
    openai_request_id = Column(String(255), nullable=True)

    # Relationships
    session = relationship("Session", back_populates="transcript")


class SessionResponse(Base, TimestampMixin):
    """
    AI-generated response for each checklist item in a session
    """
    __tablename__ = "session_responses"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    item_id = Column(Integer, ForeignKey("checklist_items.id", ondelete="CASCADE"), nullable=False)

    # AI Response
    is_validated = Column(Boolean, nullable=True)  # True/False/None (not found)
    confidence = Column(Float, nullable=True)  # 0.0 - 1.0
    evidence_text = Column(Text, nullable=True)  # Quote from transcript
    ai_reasoning = Column(Text, nullable=True)  # Why AI made this decision

    # Manual override by admin/manager
    manual_override = Column(Boolean, nullable=True)
    override_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    override_reason = Column(Text, nullable=True)

    # Relationships
    session = relationship("Session", back_populates="responses")
    item = relationship("ChecklistItem", back_populates="session_responses")
