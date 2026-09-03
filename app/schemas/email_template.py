"""Schemas for Super Admin email template editor."""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class EmailTemplateListItem(BaseModel):
    slug: str
    name: str
    description: str = ""
    updated_at: Optional[datetime] = None


class EmailTemplateDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    slug: str
    name: str
    description: str = ""
    subject: str
    html_body: str
    variables: List[str] = Field(default_factory=list)
    sample_context: Dict[str, Any] = Field(default_factory=dict)
    updated_at: Optional[datetime] = None
    updated_by_user_id: Optional[int] = None


class EmailTemplateUpdate(BaseModel):
    subject: str
    html_body: str


class EmailTemplatePreviewRequest(BaseModel):
    subject: Optional[str] = None
    html_body: Optional[str] = None


class EmailTemplatePreviewResponse(BaseModel):
    subject: str
    html_body: str


class EmailTemplateTestRequest(BaseModel):
    to_email: str


class EmailTemplateTestResponse(BaseModel):
    sent: bool
    to_email: str
    subject: str
