"""
Pydantic schemas for Session endpoints
"""
from pydantic import BaseModel, Field, field_serializer
from typing import Optional, List, Literal
from datetime import datetime
from app.models.session import SessionStatus, SessionMode


class SessionCreate(BaseModel):
    """Schema for creating a session"""
    customer_name: str = Field(..., min_length=1, max_length=255)
    opportunity_name: Optional[str] = Field(None, max_length=255)
    decision_influencer: Optional[str] = Field(None, max_length=255)
    deal_stage: Optional[str] = Field(None, max_length=100)
    session_mode: Literal["audio", "manual"] = Field(
        default="audio",
        description="Session input mode: 'audio' (record audio) or 'manual' (fill checklist manually)"
    )


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
    session_mode: SessionMode
    status: SessionStatus
    submitted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    # Convert session_mode to lowercase for API consistency
    @field_serializer('session_mode')
    def serialize_session_mode(self, value: SessionMode) -> str:
        return value.value.lower()

    class Config:
        from_attributes = True


class SessionListResponse(BaseModel):
    """Response schema for session list"""
    sessions: List[SessionResponse]
    total: int
    page: int
    page_size: int


# Manual Checklist Schemas

class ManualChecklistItem(BaseModel):
    """Schema for a single manual checklist item submission"""
    item_id: int = Field(..., description="Checklist item ID")
    answer: bool = Field(..., description="True = Yes (10 pts), False = No (0 pts)")
    notes: Optional[str] = Field(None, max_length=1000, description="Optional user notes for context")


class ManualChecklistSubmit(BaseModel):
    """Schema for submitting a manually filled checklist"""
    responses: List[ManualChecklistItem] = Field(..., min_length=1, description="List of checklist item responses")

    class Config:
        json_schema_extra = {
            "example": {
                "responses": [
                    {"item_id": 1, "answer": True, "notes": "Discussed in detail"},
                    {"item_id": 2, "answer": False, "notes": "Missed this point"}
                ]
            }
        }
