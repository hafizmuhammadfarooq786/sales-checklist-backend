"""Pending public organization signup requests awaiting Super Admin approval."""
import enum

from sqlalchemy import Column, DateTime, Enum as SQLEnum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB

from app.models.base import Base, TimestampMixin


class RegistrationStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class OrganizationRegistrationRequest(Base, TimestampMixin):
    __tablename__ = "organization_registration_requests"

    id = Column(Integer, primary_key=True, index=True)
    status = Column(
        SQLEnum(
            RegistrationStatus,
            name="organizationregistrationstatus",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        default=RegistrationStatus.PENDING,
        nullable=False,
        index=True,
    )

    company_name = Column(String(255), nullable=False)
    industry = Column(String(100), nullable=False)
    logo_url = Column(Text, nullable=True)

    admin_first_name = Column(String(100), nullable=False)
    admin_last_name = Column(String(100), nullable=False)
    admin_email = Column(String(255), nullable=False, index=True)
    admin_direct_dial = Column(String(50), nullable=False)
    admin_cell_phone = Column(String(50), nullable=True)

    additional_users = Column(JSONB, nullable=False, default=list)

    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_by = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
