"""
Organization Schemas
Pydantic models for organization and settings validation
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, EmailStr, Field, field_validator
import re

from app.models.user import UserRole
from app.utils.us_phone_validation import validate_us_phone_value

PHONE_PATTERN = re.compile(r"^[\d\s+\-().extEXT#]{7,30}$")

INDUSTRY_OPTIONS: List[str] = [
    "Technology",
    "Financial Services",
    "Healthcare",
    "Manufacturing",
    "Retail",
    "Professional Services",
    "Education",
    "Government",
    "Real Estate",
    "Telecommunications",
    "Energy",
    "Other",
]


def _validate_phone_optional(value: Optional[str]) -> Optional[str]:
    error = validate_us_phone_value(value, required=False)
    if error:
        raise ValueError(error)
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    digits = re.sub(r"\D", "", cleaned)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    return cleaned


class OrganizationBase(BaseModel):
    """Base organization schema"""
    name: str = Field(..., min_length=1, max_length=255)


class OrganizationCreate(OrganizationBase):
    """Schema for creating an organization"""
    pass


class OrganizationUpdate(BaseModel):
    """Schema for updating an organization"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    is_active: Optional[bool] = None


class OrganizationAdminUpdate(BaseModel):
    """Org admin can update company profile fields."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    industry: Optional[str] = Field(None, max_length=100)

    @field_validator("industry", mode="before")
    @classmethod
    def normalize_industry(cls, v: Optional[str]) -> Optional[str]:
        if v is None or not str(v).strip():
            return None
        return str(v).strip()


class OrganizationResponse(OrganizationBase):
    """Schema for organization response"""
    id: int
    industry: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OrganizationSettingsBase(BaseModel):
    """Base organization settings schema"""
    allow_self_registration: bool = False
    default_role: str = Field("rep", pattern="^(rep|manager|admin|executive)$")
    logo_url: Optional[str] = None
    primary_color: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")
    executive_sponsor_name: Optional[str] = Field(None, max_length=255)
    executive_sponsor_email: Optional[EmailStr] = None
    executive_sponsor_direct_dial: Optional[str] = Field(None, max_length=50)
    executive_sponsor_cell_phone: Optional[str] = Field(None, max_length=50)
    settings: Optional[Dict[str, Any]] = None

    @field_validator("default_role", mode="before")
    @classmethod
    def normalize_default_role(cls, v: Optional[str]) -> str:
        if v is None or v == "":
            return "rep"
        return v.strip().lower()

    @field_validator("executive_sponsor_direct_dial", "executive_sponsor_cell_phone", mode="before")
    @classmethod
    def validate_sponsor_phones(cls, v: Optional[str]) -> Optional[str]:
        return _validate_phone_optional(v)


class OrganizationSettingsUpdate(BaseModel):
    """Schema for updating organization settings"""
    allow_self_registration: Optional[bool] = None
    default_role: Optional[str] = Field(None, pattern="^(rep|manager|admin|executive)$")
    logo_url: Optional[str] = None
    primary_color: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")
    executive_sponsor_name: Optional[str] = Field(None, max_length=255)
    executive_sponsor_email: Optional[EmailStr] = None
    executive_sponsor_direct_dial: Optional[str] = Field(None, max_length=50)
    executive_sponsor_cell_phone: Optional[str] = Field(None, max_length=50)
    settings: Optional[Dict[str, Any]] = None

    @field_validator("default_role", mode="before")
    @classmethod
    def normalize_default_role_update(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        return v.strip().lower()

    @field_validator("executive_sponsor_direct_dial", "executive_sponsor_cell_phone", mode="before")
    @classmethod
    def validate_sponsor_phones(cls, v: Optional[str]) -> Optional[str]:
        return _validate_phone_optional(v)


class OrganizationSettingsResponse(OrganizationSettingsBase):
    """Schema for organization settings response"""
    id: int
    organization_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OrganizationProfileResponse(BaseModel):
    """Combined org + settings for admin company form."""
    organization: OrganizationResponse
    settings: OrganizationSettingsResponse
    executive_sponsor: "ExecutiveSponsorResponse"


class ExecutiveSponsorResponse(BaseModel):
    """Organization admin — the executive sponsor for the org."""
    user_id: int
    name: str
    email: EmailStr
    direct_dial: Optional[str] = None
    cell_phone: Optional[str] = None
    role: str = "Administrator"


class OrganizationProfileUpdate(BaseModel):
    """Single save payload for company profile form."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    industry: Optional[str] = Field(None, max_length=100)
    allow_self_registration: Optional[bool] = None
    default_role: Optional[str] = Field(None, pattern="^(rep|manager|admin|executive)$")
    direct_dial: Optional[str] = Field(None, max_length=50)
    cell_phone: Optional[str] = Field(None, max_length=50)

    @field_validator("industry", mode="before")
    @classmethod
    def normalize_industry(cls, v: Optional[str]) -> Optional[str]:
        if v is None or not str(v).strip():
            return None
        return str(v).strip()

    @field_validator("default_role", mode="before")
    @classmethod
    def normalize_default_role(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        return v.strip().lower()

    @field_validator("direct_dial", "cell_phone", mode="before")
    @classmethod
    def validate_sponsor_phones(cls, v: Optional[str]) -> Optional[str]:
        return _validate_phone_optional(v)


class UserRoleSummary(BaseModel):
    """Auto-count users by role for org admin dashboard."""
    executives: int = 0
    managers: int = 0
    salespeople: int = 0
    administrators: int = 0
    total_users: int = 0


class TeamBase(BaseModel):
    """Base team schema"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class TeamCreate(TeamBase):
    """Schema for creating a team"""
    pass


class TeamUpdate(BaseModel):
    """Schema for updating a team"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None


class TeamResponse(TeamBase):
    """Schema for team response"""
    id: int
    organization_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
