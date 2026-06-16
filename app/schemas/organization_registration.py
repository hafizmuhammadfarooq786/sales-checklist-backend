"""Schemas for public organization registration and Super Admin approval."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, ValidationInfo, field_validator

from app.schemas.organization import INDUSTRY_OPTIONS, _validate_phone_optional
from app.utils.email_validation import validate_email_address
from app.models.organization_registration import RegistrationStatus


class SignupUserRow(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    role: str = Field(..., pattern="^(rep|manager)$")
    direct_dial: str = Field(..., max_length=50)
    cell_phone: Optional[str] = Field(None, max_length=50)

    @field_validator("email", mode="before")
    @classmethod
    def validate_email(cls, value: str) -> str:
        result = validate_email_address(value, required=True)
        assert result is not None
        return result

    @field_validator("role", mode="before")
    @classmethod
    def normalize_role(cls, value: str) -> str:
        return str(value).strip().lower()

    @field_validator("direct_dial", mode="before")
    @classmethod
    def validate_direct_dial(cls, value: str) -> str:
        cleaned = _validate_phone_optional(value)
        if not cleaned:
            raise ValueError("Direct dial is required")
        return cleaned

    @field_validator("cell_phone", mode="before")
    @classmethod
    def validate_cell_phone(cls, value: Optional[str]) -> Optional[str]:
        return _validate_phone_optional(value)


class OrganizationRegistrationCreate(BaseModel):
    company_name: str = Field(..., min_length=1, max_length=255)
    industry: str = Field(..., min_length=1, max_length=100)
    admin_first_name: str = Field(..., min_length=1, max_length=100)
    admin_last_name: str = Field(..., min_length=1, max_length=100)
    admin_email: EmailStr
    admin_direct_dial: str = Field(..., max_length=50)
    admin_cell_phone: Optional[str] = Field(None, max_length=50)
    additional_users: List[SignupUserRow] = Field(default_factory=list)

    @field_validator("admin_email", mode="before")
    @classmethod
    def validate_admin_email(cls, value: str) -> str:
        result = validate_email_address(value, required=True)
        assert result is not None
        return result

    @field_validator("industry", mode="before")
    @classmethod
    def normalize_industry(cls, value: str) -> str:
        cleaned = str(value).strip()
        if cleaned not in INDUSTRY_OPTIONS:
            raise ValueError("Invalid industry")
        return cleaned

    @field_validator("admin_direct_dial", mode="before")
    @classmethod
    def validate_admin_direct_dial(cls, value: str) -> str:
        cleaned = _validate_phone_optional(value)
        if not cleaned:
            raise ValueError("Direct dial is required")
        return cleaned

    @field_validator("admin_cell_phone", mode="before")
    @classmethod
    def validate_admin_cell_phone(cls, value: Optional[str]) -> Optional[str]:
        return _validate_phone_optional(value)

    @field_validator("additional_users")
    @classmethod
    def validate_unique_emails(
        cls,
        users: List[SignupUserRow],
        info: ValidationInfo,
    ) -> List[SignupUserRow]:
        admin_email = str(info.data.get("admin_email", "")).strip().lower()
        seen = {admin_email} if admin_email else set()
        for user in users:
            email = user.email.strip().lower()
            if email in seen:
                raise ValueError(f"Duplicate email in signup request: {email}")
            seen.add(email)
        return users


class SignupUserRowResponse(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    role: str
    direct_dial: str
    cell_phone: Optional[str] = None


class OrganizationRegistrationResponse(BaseModel):
    id: int
    status: RegistrationStatus
    company_name: str
    industry: str
    logo_url: Optional[str] = None
    logo_preview_base64: Optional[str] = None
    logo_content_type: Optional[str] = None
    admin_first_name: str
    admin_last_name: str
    admin_email: EmailStr
    admin_direct_dial: str
    admin_cell_phone: Optional[str] = None
    additional_users: List[SignupUserRowResponse] = Field(default_factory=list)
    organization_id: Optional[int] = None
    reviewed_by: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OrganizationRegistrationSubmitResponse(BaseModel):
    id: int
    status: RegistrationStatus
    message: str


class OrganizationRegistrationReject(BaseModel):
    reason: Optional[str] = Field(None, max_length=2000)


class OrganizationRegistrationApproveResponse(BaseModel):
    registration: OrganizationRegistrationResponse
    organization_id: int
    invitations_sent: int
    message: str


class OrganizationRegistrationResendInvitationsResponse(BaseModel):
    invitations_resent: int
    message: str
