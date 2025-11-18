"""
Report generation and exports
"""
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum

from app.models.base import Base, TimestampMixin


class ReportFormat(str, enum.Enum):
    """Report export formats"""
    PDF = "pdf"
    DOCX = "docx"
    JSON = "json"


class Report(Base, TimestampMixin):
    """
    Generated reports for sessions
    """
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, unique=True)

    # PDF report
    pdf_s3_bucket = Column(String(255), nullable=True)
    pdf_s3_key = Column(String(500), nullable=True)
    pdf_file_size = Column(Integer, nullable=True)

    # Generation
    generated_at = Column(DateTime, nullable=True)
    is_generated = Column(Boolean, default=False)

    # Email delivery
    emailed_at = Column(DateTime, nullable=True)
    emailed_to = Column(String(255), nullable=True)

    # Relationships
    session = relationship("Session", back_populates="report")


class SalesforceSync(Base, TimestampMixin):
    """
    Salesforce integration sync logs
    """
    __tablename__ = "salesforce_sync"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)

    # Salesforce details
    salesforce_object_type = Column(String(100), nullable=False)  # Lead, Opportunity, etc.
    salesforce_object_id = Column(String(255), nullable=True)  # Salesforce record ID

    # Sync status
    is_synced = Column(Boolean, default=False)
    synced_at = Column(DateTime, nullable=True)
    sync_error = Column(String(1000), nullable=True)

    # Data synced
    fields_synced = Column(String(1000), nullable=True)  # JSON string of field names
