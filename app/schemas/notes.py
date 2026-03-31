"""
Pydantic schemas for opportunity-scoped checklist item notes.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict


class DecisionInfluencerIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=500)
    title: Optional[str] = Field(None, max_length=500)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=100)

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, v: str) -> str:
        if isinstance(v, str):
            v = v.strip()
        if not v:
            raise ValueError("name cannot be empty")
        return v


class NoteUpsertBody(BaseModel):
    """Payload for single-item upsert."""

    note_text: Optional[str] = None
    decision_influencers: Optional[List[DecisionInfluencerIn]] = None
    structured_content: Optional[Dict[str, Any]] = None

    @field_validator("note_text", mode="before")
    @classmethod
    def strip_note(cls, v: Optional[str]) -> Optional[str]:
        if v is None or not isinstance(v, str):
            return v
        v = v.strip()
        return v if v else None


class NoteBulkItemIn(BaseModel):
    checklist_item_id: int = Field(..., ge=1)
    note_text: Optional[str] = None
    decision_influencers: Optional[List[DecisionInfluencerIn]] = None
    structured_content: Optional[Dict[str, Any]] = None

    @field_validator("note_text", mode="before")
    @classmethod
    def strip_note(cls, v: Optional[str]) -> Optional[str]:
        if v is None or not isinstance(v, str):
            return v
        v = v.strip()
        return v if v else None


class NotesBulkUpsertRequest(BaseModel):
    items: List[NoteBulkItemIn] = Field(..., min_length=1)

    @field_validator("items", mode="after")
    @classmethod
    def no_duplicate_items(cls, v: List[NoteBulkItemIn]) -> List[NoteBulkItemIn]:
        ids = [i.checklist_item_id for i in v]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate checklist_item_id in items")
        return v


class NoteUserBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class NoteLatestOut(BaseModel):
    id: int
    checklist_item_id: int
    note_text: Optional[str] = None
    decision_influencers: Optional[List[dict[str, Any]]] = None
    structured_content: Optional[Dict[str, Any]] = None
    version: int
    updated_at: datetime
    updated_by: Optional[NoteUserBrief] = None
    session_id: Optional[int] = None


class NoteSlotOut(BaseModel):
    checklist_item_id: int
    note: Optional[NoteLatestOut] = None


class NotesSessionBundleOut(BaseModel):
    session_id: int
    customer_name: str
    opportunity_name: str
    opportunity_key: str
    items: List[NoteSlotOut]


class NoteItemSingleOut(BaseModel):
    """Latest note for one checklist item (or null if none)."""

    checklist_item_id: int
    note: Optional[NoteLatestOut] = None


class NoteHistoryEntryOut(BaseModel):
    version: int
    note_text: Optional[str] = None
    decision_influencers: Optional[List[dict[str, Any]]] = None
    structured_content: Optional[Dict[str, Any]] = None
    updated_by: Optional[NoteUserBrief] = None
    updated_at: datetime
    session_id: Optional[int] = None


class NotesBulkUpsertResponse(BaseModel):
    session_id: int
    customer_name: str
    opportunity_name: str
    opportunity_key: str
    items: List[NoteLatestOut]
