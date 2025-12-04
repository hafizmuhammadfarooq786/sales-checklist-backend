"""
Pydantic schemas for Session endpoints
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.models.session import SessionStatus


class SessionCreate(BaseModel):
    """Schema for creating a session"""
    customer_name: str = Field(..., min_length=1, max_length=255)
    opportunity_name: Optional[str] = Field(None, max_length=255)
    decision_influencer: Optional[str] = Field(None, max_length=255)
    deal_stage: Optional[str] = Field(None, max_length=100)


class SessionUpdate(BaseModel):
    """Schema for updating a session"""
    customer_name: Optional[str] = Field(None, max_length=255)
    opportunity_name: Optional[str] = Field(None, max_length=255)
    decision_influencer: Optional[str] = Field(None, max_length=255)
    deal_stage: Optional[str] = Field(None, max_length=100)
    status: Optional[SessionStatus] = None


class SessionResponse(BaseModel):
    """Response schema for sessions"""
    id: int
    user_id: int
    customer_name: str
    opportunity_name: Optional[str] = None
    decision_influencer: Optional[str] = None
    deal_stage: Optional[str] = None
    status: SessionStatus
    submitted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SessionListResponse(BaseModel):
    """Response schema for session list"""
    sessions: List[SessionResponse]
    total: int
    page: int
    page_size: int
