"""
Pydantic schemas for Manager Notes
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class ManagerNoteBase(BaseModel):
    """Base schema for manager notes"""
    note_text: str = Field(..., min_length=1, max_length=5000, description="Note content")


class ManagerNoteCreate(ManagerNoteBase):
    """Schema for creating a new manager note"""
    pass


class ManagerNoteUpdate(BaseModel):
    """Schema for updating an existing manager note"""
    note_text: str = Field(..., min_length=1, max_length=5000, description="Updated note content")


class ManagerNoteResponse(ManagerNoteBase):
    """Response schema for manager notes"""
    id: int
    session_id: int
    manager_id: int
    manager_name: Optional[str] = None  # Computed field: manager's full name
    is_edited: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ManagerNoteListResponse(BaseModel):
    """Response schema for list of notes on a session"""
    session_id: int
    notes: list[ManagerNoteResponse]
    total_notes: int
