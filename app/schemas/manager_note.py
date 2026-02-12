"""
Pydantic schemas for Manager Notes
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class ManagerNoteBase(BaseModel):
    """Base schema for manager notes"""
    note_text: Optional[str] = Field(None, min_length=1, max_length=5000, description="Note content (for text notes)")


class ManagerNoteCreate(ManagerNoteBase):
    """Schema for creating a new text manager note"""
    note_text: str = Field(..., min_length=1, max_length=5000, description="Note content")


class ManagerNoteUpdate(BaseModel):
    """Schema for updating an existing text manager note"""
    note_text: str = Field(..., min_length=1, max_length=5000, description="Updated note content")


class ManagerNoteResponse(BaseModel):
    """Response schema for manager notes (text or audio)"""
    id: int
    session_id: int
    manager_id: int
    manager_name: Optional[str] = None  # Computed field: manager's full name
    note_type: str  # "text" or "audio"
    note_text: Optional[str] = None  # For text notes
    is_edited: bool

    # Audio fields (for audio notes)
    audio_url: Optional[str] = None  # Presigned URL or direct URL
    audio_duration: Optional[int] = None  # Duration in seconds
    audio_file_size: Optional[int] = None  # File size in bytes

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ManagerNoteListResponse(BaseModel):
    """Response schema for list of notes on a session"""
    session_id: int
    notes: list[ManagerNoteResponse]
    total_notes: int
