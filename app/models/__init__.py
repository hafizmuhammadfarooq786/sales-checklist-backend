"""
SQLAlchemy models - Import all for Alembic autogenerate
"""
from app.models.base import Base, TimestampMixin

# Import all models
from app.models.user import Organization, Team, User, UserRole
from app.models.checklist import ChecklistCategory, ChecklistItem, CoachingQuestion
from app.models.checklist_behaviour import ChecklistItemBehaviour, SessionResponseAnalysis
from app.models.session import (
    Session,
    SessionStatus,
    AudioFile,
    Transcript,
    SessionResponse,
)
from app.models.scoring import ScoringResult, CoachingFeedback, RiskBand, ScoreHistory
from app.models.report import Report, ReportFormat
from app.models.invitation import Invitation
from app.models.organization_settings import OrganizationSettings

# Export all for easy imports
__all__ = [
    "Base",
    "TimestampMixin",
    "Organization",
    "Team",
    "User",
    "UserRole",
    "ChecklistCategory",
    "ChecklistItem",
    "CoachingQuestion",
    "ChecklistItemBehaviour",
    "SessionResponseAnalysis",
    "Session",
    "SessionStatus",
    "AudioFile",
    "Transcript",
    "SessionResponse",
    "ScoringResult",
    "ScoreHistory",
    "CoachingFeedback",
    "RiskBand",
    "Report",
    "ReportFormat",
    "Invitation",
    "OrganizationSettings",
]
