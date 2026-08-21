"""
ActivityEmitter — write first-party activity events (no third-party analytics).
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.request_context import get_request_context
from app.models.activity_event import ActivityEvent

logger = logging.getLogger(__name__)

# Never persist secrets / free-text deal content
_BLOCKED_PAYLOAD_KEYS: Set[str] = {
    "password",
    "temp_password",
    "token",
    "access_token",
    "refresh_token",
    "authorization",
    "secret",
    "api_key",
    "transcript",
    "audio",
}


def _sanitize_payload(payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not payload:
        return {}
    clean: Dict[str, Any] = {}
    for key, value in payload.items():
        key_l = str(key).lower()
        if key_l in _BLOCKED_PAYLOAD_KEYS or any(b in key_l for b in ("password", "token", "secret")):
            continue
        if isinstance(value, dict):
            clean[key] = _sanitize_payload(value)
        elif isinstance(value, (str, int, float, bool)) or value is None:
            if isinstance(value, str) and len(value) > 500:
                clean[key] = value[:500]
            else:
                clean[key] = value
        elif isinstance(value, list):
            # Keep short primitive lists only
            if all(isinstance(v, (str, int, float, bool)) or v is None for v in value[:20]):
                clean[key] = value[:20]
    return clean


class ActivityEmitter:
    async def emit(
        self,
        db: AsyncSession,
        *,
        event_type: str,
        organization_id: Optional[int] = None,
        actor_user_id: Optional[int] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[Any] = None,
        payload: Optional[Dict[str, Any]] = None,
        parent_event_id: Optional[str] = None,
        commit: bool = False,
    ) -> Optional[ActivityEvent]:
        """
        Append an activity event.

        By default only flushes into the caller's transaction (`commit=False`).
        Pass `commit=True` when the business write already committed.
        """
        try:
            ctx = get_request_context()
            event = ActivityEvent(
                id=str(uuid4()),
                occurred_at=datetime.utcnow(),
                organization_id=organization_id,
                actor_user_id=actor_user_id,
                event_type=event_type,
                resource_type=resource_type,
                resource_id=str(resource_id) if resource_id is not None else None,
                trace_id=ctx.trace_id,
                parent_event_id=parent_event_id,
                payload=_sanitize_payload(payload),
                ip_address=(ctx.ip_address[:64] if ctx.ip_address else None),
                user_agent=ctx.user_agent,
            )
            db.add(event)
            if commit:
                await db.commit()
                await db.refresh(event)
            else:
                await db.flush()
            return event
        except Exception:
            logger.exception("Failed to emit activity event type=%s", event_type)
            # Never break the primary business path because of telemetry
            if commit:
                try:
                    await db.rollback()
                except Exception:
                    pass
            return None

    async def list_for_organization(
        self,
        db: AsyncSession,
        *,
        organization_id: int,
        event_type: Optional[str] = None,
        event_type_prefix: Optional[str] = None,
        from_dt: Optional[datetime] = None,
        to_dt: Optional[datetime] = None,
        limit: int = 50,
        cursor_occurred_at: Optional[datetime] = None,
        cursor_id: Optional[str] = None,
    ) -> List[ActivityEvent]:
        query = (
            select(ActivityEvent)
            .options(
                selectinload(ActivityEvent.actor),
                selectinload(ActivityEvent.organization),
            )
            .where(ActivityEvent.organization_id == organization_id)
        )
        if event_type:
            query = query.where(ActivityEvent.event_type == event_type)
        elif event_type_prefix:
            query = query.where(ActivityEvent.event_type.like(f"{event_type_prefix}%"))
        if from_dt:
            query = query.where(ActivityEvent.occurred_at >= from_dt)
        if to_dt:
            query = query.where(ActivityEvent.occurred_at <= to_dt)
        if cursor_occurred_at is not None and cursor_id:
            query = query.where(
                (ActivityEvent.occurred_at < cursor_occurred_at)
                | and_(
                    ActivityEvent.occurred_at == cursor_occurred_at,
                    ActivityEvent.id < cursor_id,
                )
            )
        query = query.order_by(
            ActivityEvent.occurred_at.desc(), ActivityEvent.id.desc()
        ).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def list_recent(
        self,
        db: AsyncSession,
        *,
        organization_id: Optional[int] = None,
        event_type: Optional[str] = None,
        event_type_prefix: Optional[str] = None,
        from_dt: Optional[datetime] = None,
        limit: int = 40,
    ) -> List[ActivityEvent]:
        query = select(ActivityEvent).options(
            selectinload(ActivityEvent.actor),
            selectinload(ActivityEvent.organization),
        )
        if organization_id is not None:
            query = query.where(ActivityEvent.organization_id == organization_id)
        if event_type:
            query = query.where(ActivityEvent.event_type == event_type)
        elif event_type_prefix:
            query = query.where(ActivityEvent.event_type.like(f"{event_type_prefix}%"))
        if from_dt:
            query = query.where(ActivityEvent.occurred_at >= from_dt)
        query = query.order_by(
            ActivityEvent.occurred_at.desc(), ActivityEvent.id.desc()
        ).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_event(self, db: AsyncSession, event_id: str) -> Optional[ActivityEvent]:
        result = await db.execute(
            select(ActivityEvent)
            .options(
                selectinload(ActivityEvent.actor),
                selectinload(ActivityEvent.organization),
            )
            .where(ActivityEvent.id == event_id)
        )
        return result.scalar_one_or_none()

    async def list_trace(self, db: AsyncSession, trace_id: str) -> List[ActivityEvent]:
        result = await db.execute(
            select(ActivityEvent)
            .options(
                selectinload(ActivityEvent.actor),
                selectinload(ActivityEvent.organization),
            )
            .where(ActivityEvent.trace_id == trace_id)
            .order_by(ActivityEvent.occurred_at.asc(), ActivityEvent.id.asc())
        )
        return list(result.scalars().all())


activity_emitter = ActivityEmitter()
