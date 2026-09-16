"""
Pydantic schemas for User endpoints
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from app.models.user import UserRole


class UserBase(BaseModel):
    """Base schema for users"""
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    job_title: Optional[str] = Field(None, max_length=150)
    direct_dial: Optional[str] = Field(None, max_length=50)
    cell_phone: Optional[str] = Field(None, max_length=50)


class UserCreate(UserBase):
    """Schema for creating a user via registration"""
    role: UserRole = UserRole.REP


class UserUpdate(BaseModel):
    """Schema for updating a user"""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    job_title: Optional[str] = Field(None, max_length=150)
    direct_dial: Optional[str] = Field(None, max_length=50)
    cell_phone: Optional[str] = Field(None, max_length=50)
    role: Optional[UserRole] = None
    team_id: Optional[int] = None
    is_active: Optional[bool] = None


class UserSelfUpdate(BaseModel):
    """Schema for self-service profile updates (safe fields only)"""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    job_title: Optional[str] = Field(None, max_length=150)
    direct_dial: Optional[str] = Field(None, max_length=50)
    cell_phone: Optional[str] = Field(None, max_length=50)


class AdminUserProvision(UserBase):
    """Schema for SYSTEM_ADMIN-provisioned users"""
    organization_id: int
    team_id: Optional[int] = None
    role: UserRole = UserRole.REP
    is_active: bool = True
    is_verified: bool = True


class UserResponse(UserBase):
    """Response schema for users"""
    id: int
    role: UserRole
    organization_id: Optional[int] = None
    team_id: Optional[int] = None
    is_active: bool
    is_verified: bool
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TeamResponse(BaseModel):
    """Response schema for teams"""
    id: int
    organization_id: int
    name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OrganizationResponse(BaseModel):
    """Response schema for organizations"""
    id: int
    name: str
    industry: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OtpRequest(BaseModel):
    """Request an email OTP for passwordless sign-in."""
    email: EmailStr


class EmailRequest(BaseModel):
    """Email-only payload for resend-verification and similar public flows."""
    email: EmailStr


class OtpVerify(BaseModel):
    """Verify an email OTP and issue a JWT session."""
    email: EmailStr
    code: str = Field(min_length=6, max_length=8, description="6-digit email verification code")
    remember_me: bool = True


class Token(BaseModel):
    """JWT Token response schema"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class EmailVerification(BaseModel):
    """Schema for email verification"""
    token: str


class PipelineMetrics(BaseModel):
    """Response schema for user pipeline metrics"""
    total_sessions: int = Field(description="Total number of sessions")
    active_sessions: int = Field(description="Sessions not in draft, failed, or completed status")
    completed_sessions: int = Field(description="Successfully completed sessions")
    total_opportunities: int = Field(description="Total unique opportunities")

    class Config:
        from_attributes = True
