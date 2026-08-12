"""Auth session schemas for Super Admin visibility (P1)."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class AuthSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: int
    organization_id: Optional[int] = None
    user_email: Optional[str] = None
    user_name: Optional[str] = None
    created_at: datetime
    expires_at: datetime
    last_seen_at: datetime
    revoked_at: Optional[datetime] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    remember_me: bool = False
    is_active: bool = False
