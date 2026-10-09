"""Managers share a session with other salespeople in the organization."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies import check_session_access, get_current_active_user
from app.db.session import get_db
from app.models.session import Session
from app.models.session_share import SessionShare
from app.models.user import User, UserRole

router = APIRouter()

READ_PERMISSION = "read"


class SessionShareUser(BaseModel):
    id: int
    user_id: int
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    permission: str


class SessionShareCandidate(BaseModel):
    user_id: int
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class SessionShareCreate(BaseModel):
    user_id: int


def _user_brief(user: User) -> dict:
    return {
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
    }


async def _require_manager_session(
    session_id: int,
    current_user: User,
    db: AsyncSession,
) -> Session:
    if current_user.role != UserRole.MANAGER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only a manager can share this checklist",
        )
    if not await check_session_access(session_id, current_user, db, write=True):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    result = await db.execute(
        select(Session)
        .where(Session.id == session_id)
        .options(selectinload(Session.user))
    )
    session = result.scalar_one_or_none()
    if session is None or session.user is None or session.user.organization_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    return session


@router.get("/{session_id}/shares", response_model=List[SessionShareUser])
async def list_session_shares(
    session_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    await _require_manager_session(session_id, current_user, db)
    result = await db.execute(
        select(SessionShare)
        .where(SessionShare.session_id == session_id)
        .options(selectinload(SessionShare.user))
        .order_by(SessionShare.created_at.asc())
    )
    shares = result.scalars().all()
    return [
        SessionShareUser(
            id=share.id,
            user_id=share.user_id,
            permission=share.permission,
            **_user_brief(share.user),
        )
        for share in shares
        if share.user is not None
    ]


@router.get(
    "/{session_id}/share-candidates",
    response_model=List[SessionShareCandidate],
)
async def list_share_candidates(
    session_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    session = await _require_manager_session(session_id, current_user, db)
    already = await db.execute(
        select(SessionShare.user_id).where(SessionShare.session_id == session_id)
    )
    taken = {row[0] for row in already.all()}
    taken.add(session.user_id)
    result = await db.execute(
        select(User)
        .where(
            User.organization_id == session.user.organization_id,
            User.role == UserRole.REP,
            User.deleted_at.is_(None),
            User.is_active.is_(True),
            User.id.notin_(list(taken)),
        )
        .order_by(User.first_name.asc(), User.email.asc())
    )
    users = result.scalars().all()
    return [
        SessionShareCandidate(user_id=user.id, **_user_brief(user))
        for user in users
    ]


@router.post(
    "/{session_id}/shares",
    response_model=SessionShareUser,
    status_code=status.HTTP_201_CREATED,
)
async def add_session_share(
    session_id: int,
    body: SessionShareCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    session = await _require_manager_session(session_id, current_user, db)
    if body.user_id == session.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The salesperson who created this checklist already has access",
        )
    result = await db.execute(
        select(User).where(
            User.id == body.user_id,
            User.organization_id == session.user.organization_id,
            User.role == UserRole.REP,
            User.deleted_at.is_(None),
            User.is_active.is_(True),
        )
    )
    salesperson = result.scalar_one_or_none()
    if salesperson is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Choose an active salesperson in this organization",
        )
    existing = await db.execute(
        select(SessionShare).where(
            SessionShare.session_id == session_id,
            SessionShare.user_id == salesperson.id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This salesperson can already view the checklist",
        )
    share = SessionShare(
        session_id=session_id,
        user_id=salesperson.id,
        permission=READ_PERMISSION,
        added_by_user_id=current_user.id,
    )
    db.add(share)
    await db.commit()
    await db.refresh(share)
    return SessionShareUser(
        id=share.id,
        user_id=salesperson.id,
        permission=share.permission,
        **_user_brief(salesperson),
    )


@router.delete(
    "/{session_id}/shares/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_session_share(
    session_id: int,
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    await _require_manager_session(session_id, current_user, db)
    result = await db.execute(
        select(SessionShare).where(
            SessionShare.session_id == session_id,
            SessionShare.user_id == user_id,
        )
    )
    share = result.scalar_one_or_none()
    if share is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This salesperson is not on the checklist",
        )
    await db.delete(share)
    await db.commit()
