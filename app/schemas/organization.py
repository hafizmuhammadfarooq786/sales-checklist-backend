"""
Organization Schemas
Pydantic models for organization and settings validation
"""
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


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


class OrganizationResponse(OrganizationBase):
    """Schema for organization response"""
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OrganizationSettingsBase(BaseModel):
    """Base organization settings schema"""
    allow_self_registration: bool = False
    default_role: str = Field("rep", pattern="^(rep|manager|admin)$")
    logo_url: Optional[str] = None
    primary_color: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")
    settings: Optional[Dict[str, Any]] = None


class OrganizationSettingsUpdate(BaseModel):
    """Schema for updating organization settings"""
    allow_self_registration: Optional[bool] = None
    default_role: Optional[str] = Field(None, pattern="^(rep|manager|admin)$")
    logo_url: Optional[str] = None
    primary_color: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")
    settings: Optional[Dict[str, Any]] = None


class OrganizationSettingsResponse(OrganizationSettingsBase):
    """Schema for organization settings response"""
    id: int
    organization_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


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
