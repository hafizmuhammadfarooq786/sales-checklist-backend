"""
Manager Notes Model - Coaching feedback from managers on sessions
"""
from sqlalchemy import Column, Integer, Text, Boolean, ForeignKey, DateTime, String, Enum
from sqlalchemy.orm import relationship
import enum

from app.models.base import Base, TimestampMixin


class NoteType(str, enum.Enum):
    """Type of manager note"""
    TEXT = "text"
    AUDIO = "audio"


class ManagerNote(Base, TimestampMixin):
    """
    Manager notes/coaching feedback on sessions

    - Managers (or Admins) can leave coaching notes on any session they can view
    - Reps can view notes left on their own sessions
    - Notes can be text or audio
    - Notes are editable by the manager who wrote them (text only)
    - Multiple notes can be added to a session (conversation/thread style)
    """
    __tablename__ = "manager_notes"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    manager_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Note type and content
    note_type = Column(Enum(NoteType), default=NoteType.TEXT, nullable=False, index=True)
    note_text = Column(Text, nullable=True)  # Required for text notes, null for audio
    is_edited = Column(Boolean, default=False, nullable=False)  # Track if note was edited

    # Audio fields (for audio notes)
    audio_s3_bucket = Column(String(255), nullable=True)  # S3 bucket name (or None for local)
    audio_s3_key = Column(String(512), nullable=True)  # S3 key or local file path
    audio_duration = Column(Integer, nullable=True)  # Duration in seconds
    audio_file_size = Column(Integer, nullable=True)  # File size in bytes

    # Relationships
    session = relationship("Session", back_populates="manager_notes")
    manager = relationship("User", foreign_keys=[manager_id])  # Manager who wrote the note

    def __repr__(self):
        return f"<ManagerNote(id={self.id}, type={self.note_type}, session_id={self.session_id}, manager_id={self.manager_id})>"
