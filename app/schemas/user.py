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
    """Schema for creating a user (from Clerk webhook)"""
    clerk_user_id: str
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
    clerk_user_id: str
    role: UserRole
    organization_id: Optional[int] = None
    team_id: Optional[int] = None
    is_active: bool
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
