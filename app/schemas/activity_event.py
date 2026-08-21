"""Activity event schemas for Super Admin feed / traces (P2)."""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ActivityEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    occurred_at: datetime
    organization_id: Optional[int] = None
    organization_name: Optional[str] = None
    actor_user_id: Optional[int] = None
    actor_email: Optional[str] = None
    actor_name: Optional[str] = None
    event_type: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    trace_id: str
    parent_event_id: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class ActivityEventListResponse(BaseModel):
    items: List[ActivityEventResponse] = Field(default_factory=list)
    next_cursor: Optional[str] = None


class ActivityEventDetailResponse(ActivityEventResponse):
    related_events: List[ActivityEventResponse] = Field(default_factory=list)


class ActivityTraceResponse(BaseModel):
    trace_id: str
    events: List[ActivityEventResponse] = Field(default_factory=list)
