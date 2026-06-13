"""
Invitation Schemas
Pydantic models for invitation validation
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
import re

from app.utils.us_phone_validation import validate_us_phone_value

PHONE_PATTERN = re.compile(r"^[\d\s+\-().extEXT#]{7,30}$")


def _validate_phone_optional(value: Optional[str]) -> Optional[str]:
    error = validate_us_phone_value(value, required=False)
    if error:
        raise ValueError(error)
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    return cleaned


class InvitationBase(BaseModel):
    """Base invitation schema"""
    email: EmailStr
    team_id: Optional[int] = None
    role: str = Field(..., pattern="^(rep|manager|admin|executive)$")
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    direct_dial: Optional[str] = Field(None, max_length=50)
    cell_phone: Optional[str] = Field(None, max_length=50)

    @field_validator("role", mode="before")
    @classmethod
    def normalize_role(cls, v: str) -> str:
        if v is None or (isinstance(v, str) and v.strip() == ""):
            return "rep"
        return v.strip().lower() if isinstance(v, str) else v

    @field_validator("direct_dial", mode="before")
    @classmethod
    def validate_direct_dial(cls, v: Optional[str]) -> Optional[str]:
        if v is None or not str(v).strip():
            return None
        return _validate_phone_optional(v)

    @field_validator("cell_phone", mode="before")
    @classmethod
    def validate_cell_phone(cls, v: Optional[str]) -> Optional[str]:
        return _validate_phone_optional(v)


class InvitationCreate(InvitationBase):
    """Schema for creating an invitation"""

    @model_validator(mode="after")
    def require_user_profile(self):
        if not (self.first_name or "").strip():
            raise ValueError("First name is required")
        if not (self.last_name or "").strip():
            raise ValueError("Last name is required")
        if not (self.direct_dial or "").strip():
            raise ValueError("Direct dial is required")
        return self


class InvitationResponse(InvitationBase):
    """Schema for invitation response"""
    id: int
    organization_id: int
    token: str
    invited_by: Optional[int]
    expires_at: datetime
    accepted_at: Optional[datetime]
    created_at: datetime
    is_expired: bool
    is_accepted: bool
    is_valid: bool

    class Config:
        from_attributes = True


class InvitationAccept(BaseModel):
    """Schema for accepting an invitation"""
    token: str


class InvitationVerify(BaseModel):
    """Schema for invitation verification response"""
    valid: bool
    email: str
    organization_id: int
    organization_name: str
    team_id: Optional[int]
    team_name: Optional[str]
    role: str
    expires_at: datetime
