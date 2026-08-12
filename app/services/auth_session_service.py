"""
Auth session service — create, touch, revoke login sessions.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Optional
from uuid import uuid4

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.auth_session import AuthSession
from app.models.user import User

LAST_SEEN_THROTTLE = timedelta(minutes=5)


class AuthSessionService:
    def new_jti(self) -> str:
        return str(uuid4())

    async def create_session(
        self,
        db: AsyncSession,
        *,
        user: User,
        jti: str,
        expires_at: datetime,
        remember_me: bool = False,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuthSession:
        now = datetime.utcnow()
        session = AuthSession(
            id=jti,
            user_id=user.id,
            organization_id=user.organization_id,
            created_at=now,
            expires_at=expires_at,
            last_seen_at=now,
            revoked_at=None,
            ip_address=(ip_address[:64] if ip_address else None),
            user_agent=user_agent,
            remember_me=remember_me,
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session

    async def get_session(self, db: AsyncSession, jti: str) -> Optional[AuthSession]:
        result = await db.execute(
            select(AuthSession)
            .options(selectinload(AuthSession.user))
            .where(AuthSession.id == jti)
        )
        return result.scalar_one_or_none()

    async def assert_session_active(self, db: AsyncSession, jti: Optional[str]) -> None:
        """
        Soft mode: tokens without jti (pre-P1) are allowed.
        Tokens with jti must map to a non-revoked, non-expired session.
        """
        if not jti:
            return

        session = await self.get_session(db, jti)
        now = datetime.utcnow()
        if (
            not session
            or session.revoked_at is not None
            or session.expires_at <= now
        ):
            from fastapi import HTTPException, status

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session has been revoked or expired",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Throttle last_seen updates
        if session.last_seen_at is None or (now - session.last_seen_at) >= LAST_SEEN_THROTTLE:
            session.last_seen_at = now
            await db.commit()

    async def revoke_session(
        self, db: AsyncSession, jti: str, *, actor_user_id: Optional[int] = None
    ) -> Optional[AuthSession]:
        session = await self.get_session(db, jti)
        if not session:
            return None
        if session.revoked_at is None:
            session.revoked_at = datetime.utcnow()
            await db.commit()
            await db.refresh(session)
        return session

    async def revoke_all_for_user(self, db: AsyncSession, user_id: int) -> int:
        now = datetime.utcnow()
        result = await db.execute(
            update(AuthSession)
            .where(
                AuthSession.user_id == user_id,
                AuthSession.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )
        await db.commit()
        return int(result.rowcount or 0)

    async def list_sessions(
        self,
        db: AsyncSession,
        *,
        organization_id: Optional[int] = None,
        user_id: Optional[int] = None,
        active_only: bool = True,
        skip: int = 0,
        limit: int = 100,
    ) -> List[AuthSession]:
        now = datetime.utcnow()
        query = select(AuthSession).options(selectinload(AuthSession.user))
        if organization_id is not None:
            query = query.where(AuthSession.organization_id == organization_id)
        if user_id is not None:
            query = query.where(AuthSession.user_id == user_id)
        if active_only:
            query = query.where(
                AuthSession.revoked_at.is_(None),
                AuthSession.expires_at > now,
            )
        query = query.order_by(AuthSession.last_seen_at.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def count_active(
        self,
        db: AsyncSession,
        *,
        organization_id: Optional[int] = None,
    ) -> tuple[int, int]:
        """Return (active_sessions, distinct_active_users)."""
        now = datetime.utcnow()
        filters = [
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > now,
        ]
        if organization_id is not None:
            filters.append(AuthSession.organization_id == organization_id)

        sessions = await db.execute(
            select(func.count(AuthSession.id)).where(and_(*filters))
        )
        users = await db.execute(
            select(func.count(func.distinct(AuthSession.user_id))).where(and_(*filters))
        )
        return int(sessions.scalar() or 0), int(users.scalar() or 0)


auth_session_service = AuthSessionService()
