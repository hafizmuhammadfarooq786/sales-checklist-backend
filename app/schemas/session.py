"""
Pydantic schemas for Session endpoints
"""
from pydantic import BaseModel, Field, field_serializer, field_validator, ConfigDict
from typing import Optional, List, Literal
from datetime import datetime
from app.models.session import SessionStatus, SessionMode, DealStage


def _coerce_deal_stage(v):
    if v is None or v == "":
        return None
    if isinstance(v, DealStage):
        return v
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return None
        try:
            return DealStage(s.lower())
        except ValueError:
            key = s.upper().replace(" ", "_")
            try:
                return DealStage[key]
            except KeyError as err:
                raise ValueError(f"Invalid deal_stage: {v}") from err
    return v


class SessionCreate(BaseModel):
    """Schema for creating a session"""
    customer_name: str = Field(..., min_length=1, max_length=255)
    opportunity_name: str = Field(..., min_length=1, max_length=255)
    decision_influencer: Optional[str] = Field(None, max_length=255)
    deal_stage: Optional[DealStage] = None
    session_mode: Literal["audio", "manual"] = Field(
        default="audio",
        description="Session input mode: 'audio' (record audio) or 'manual' (fill checklist manually)"
    )

    @field_validator("deal_stage", mode="before")
    @classmethod
    def normalize_deal_stage(cls, v):
        """Accept API values as lowercase snake_case or ALL_CAPS member names."""
        return _coerce_deal_stage(v)

    @field_validator("customer_name", "opportunity_name", mode="before")
    @classmethod
    def strip_and_require(cls, v: Optional[str]) -> str:
        """
        Normalize whitespace and ensure identity fields are non-empty.
        """
        if v is None:
            raise ValueError("Field is required")
        if isinstance(v, str):
            v = v.strip()
        if not v:
            raise ValueError("Field cannot be empty")
        return v


class SessionUpdate(BaseModel):
    """Schema for updating a session (identity fields are immutable; omitted from model)."""

    model_config = ConfigDict(extra="forbid")

    decision_influencer: Optional[str] = Field(None, max_length=255)
    deal_stage: Optional[DealStage] = None
    status: Optional[SessionStatus] = None

    @field_validator("deal_stage", mode="before")
    @classmethod
    def normalize_deal_stage_update(cls, v):
        return _coerce_deal_stage(v)


class SessionResponse(BaseModel):
    """Response schema for sessions"""
    id: int
    user_id: int
    customer_name: str
    opportunity_name: str
    decision_influencer: Optional[str] = None
    deal_stage: Optional[DealStage] = None
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

    # Convert deal_stage enum to lowercase value
    @field_serializer('deal_stage')
    def serialize_deal_stage(self, value: Optional[DealStage]) -> Optional[str]:
        return value.value if value else None

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
