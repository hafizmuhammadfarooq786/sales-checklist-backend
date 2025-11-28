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


class UserCreate(UserBase):
    """Schema for creating a user via registration"""
    password: str = Field(min_length=8, description="Password must be at least 8 characters")
    role: UserRole = UserRole.REP


class UserUpdate(BaseModel):
    """Schema for updating a user"""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: Optional[UserRole] = None
    team_id: Optional[int] = None
    is_active: Optional[bool] = None


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
    description: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OrganizationResponse(BaseModel):
    """Response schema for organizations"""
    id: int
    name: str
    domain: Optional[str] = None
    is_active: bool
    scoring_mode: str
    max_users: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    """Schema for user login"""
    email: EmailStr
    password: str


class Token(BaseModel):
    """JWT Token response schema"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class PasswordReset(BaseModel):
    """Schema for password reset request"""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Schema for password reset confirmation"""
    token: str
    new_password: str = Field(min_length=8, description="Password must be at least 8 characters")


class EmailVerification(BaseModel):
    """Schema for email verification"""
    token: str


class PasswordChange(BaseModel):
    """Schema for changing password (authenticated users)"""
    current_password: str
    new_password: str = Field(min_length=8, description="New password must be at least 8 characters")


class PipelineMetrics(BaseModel):
    """Response schema for user pipeline metrics"""
    total_sessions: int = Field(description="Total number of sessions")
    active_sessions: int = Field(description="Sessions not in draft, failed, or completed status")
    completed_sessions: int = Field(description="Successfully completed sessions")
    total_opportunities: int = Field(description="Total unique opportunities")

    class Config:
        from_attributes = True
