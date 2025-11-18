"""
Session Response Pydantic schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class SessionResponseBase(BaseModel):
    """Base schema for session responses"""
    item_id: int
    is_validated: Optional[bool] = None
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    evidence_text: Optional[str] = None
    ai_reasoning: Optional[str] = None


class SessionResponseCreate(SessionResponseBase):
    """Schema for creating a session response"""
    pass


class SessionResponseUpdate(BaseModel):
    """Schema for updating a session response"""
    is_validated: Optional[bool] = None
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    evidence_text: Optional[str] = None
    ai_reasoning: Optional[str] = None
    manual_override: Optional[bool] = None
    override_reason: Optional[str] = None


class SessionResponseOut(SessionResponseBase):
    """Schema for session response output"""
    id: int
    session_id: int
    manual_override: Optional[bool] = None
    override_by_user_id: Optional[int] = None
    override_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BulkResponseCreate(BaseModel):
    """Schema for bulk creating responses"""
    responses: List[SessionResponseCreate]


class BulkResponseUpdate(BaseModel):
    """Schema for bulk updating responses"""
    responses: List[dict]  # List of {item_id: int, is_validated: bool, ...}


class SessionResponseListOut(BaseModel):
    """Schema for list of session responses with metadata"""
    session_id: int
    total_items: int
    responses: List[SessionResponseOut]
