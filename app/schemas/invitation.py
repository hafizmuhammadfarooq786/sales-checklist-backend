"""
Invitation Schemas
Pydantic models for invitation validation
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator


class InvitationBase(BaseModel):
    """Base invitation schema"""
    email: EmailStr
    team_id: Optional[int] = None
    role: str = Field(..., pattern="^(rep|manager|admin)$")

    @field_validator("role", mode="before")
    @classmethod
    def normalize_role(cls, v: str) -> str:
        if v is None or (isinstance(v, str) and v.strip() == ""):
            return "rep"
        return v.strip().lower() if isinstance(v, str) else v


class InvitationCreate(InvitationBase):
    """Schema for creating an invitation"""
    pass


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
