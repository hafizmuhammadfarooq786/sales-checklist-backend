"""
Business logic for opportunity-scoped checklist item notes.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from fastapi import HTTPException, status

from app.models.checklist import ChecklistItem
from app.models.checklist_item_note import ChecklistItemNote
from app.models.session import Session
from app.schemas.notes import (
    NoteBulkItemIn,
    NoteHistoryEntryOut,
    NoteLatestOut,
    NoteSlotOut,
    NoteUserBrief,
    NotesBulkUpsertResponse,
    NotesSessionBundleOut,
)


def normalize_identity_part(value: str) -> str:
    s = value.strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s


def compute_opportunity_key(customer_name: str, opportunity_name: str) -> str:
    c = normalize_identity_part(customer_name)
    o = normalize_identity_part(opportunity_name)
    raw = f"{c}\n{o}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def influencers_to_stored(
    rows: Optional[Sequence[Any]],
) -> Optional[List[dict[str, Any]]]:
    if not rows:
        return None
    out: List[dict[str, Any]] = []
    for r in rows:
        d = r.model_dump(mode="json") if hasattr(r, "model_dump") else dict(r)
        entry: dict[str, Any] = {"name": d.get("name")}
        if d.get("title"):
            entry["title"] = d["title"]
        if d.get("email"):
            entry["email"] = str(d["email"])
        if d.get("phone"):
            entry["phone"] = d["phone"]
        out.append(entry)
    return out


def _json_stable(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, default=str)


def _content_equal(
    active: Optional[ChecklistItemNote],
    note_text: Optional[str],
    influencers: Optional[List[dict[str, Any]]],
    structured_content: Optional[Dict[str, Any]] = None,
) -> bool:
    if active is None:
        return False
    t1 = active.note_text or None
    t2 = note_text or None
    if t1 != t2:
        return False
    if _json_stable(active.decision_influencers) != _json_stable(influencers):
        return False
    return _json_stable(active.structured_content) == _json_stable(structured_content)


def note_to_latest_out(row: ChecklistItemNote) -> NoteLatestOut:
    editor = row.updated_by_user
    sc = row.structured_content
    return NoteLatestOut(
        id=row.id,
        checklist_item_id=row.checklist_item_id,
        note_text=row.note_text,
        decision_influencers=list(row.decision_influencers)
        if row.decision_influencers is not None
        else None,
        structured_content=dict(sc) if isinstance(sc, dict) else sc,
        version=row.version,
        updated_at=row.updated_at,
        updated_by=NoteUserBrief.model_validate(editor) if editor else None,
        session_id=row.session_id,
    )


def history_entry_out(row: ChecklistItemNote) -> NoteHistoryEntryOut:
    editor = row.updated_by_user
    sc = row.structured_content
    return NoteHistoryEntryOut(
        version=row.version,
        note_text=row.note_text,
        decision_influencers=list(row.decision_influencers)
        if row.decision_influencers is not None
        else None,
        structured_content=dict(sc) if isinstance(sc, dict) else sc,
        updated_by=NoteUserBrief.model_validate(editor) if editor else None,
        updated_at=row.updated_at,
        session_id=row.session_id,
    )


async def load_session_for_notes(
    db: AsyncSession, session_id: int
) -> Optional[Session]:
    res = await db.execute(select(Session).where(Session.id == session_id))
    return res.scalar_one_or_none()


async def validate_checklist_item_ids(
    db: AsyncSession, item_ids: List[int]
) -> None:
    if not item_ids:
        return
    res = await db.execute(
        select(ChecklistItem.id).where(
            ChecklistItem.id.in_(set(item_ids)),
            ChecklistItem.is_active.is_(True),
        )
    )
    found = {r[0] for r in res.all()}
    missing = set(item_ids) - found
    if missing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown or inactive checklist_item_id(s): {sorted(missing)}",
        )


async def get_active_note(
    db: AsyncSession, checklist_item_id: int, opportunity_key: str
) -> Optional[ChecklistItemNote]:
    res = await db.execute(
        select(ChecklistItemNote)
        .where(
            ChecklistItemNote.checklist_item_id == checklist_item_id,
            ChecklistItemNote.opportunity_key == opportunity_key,
            ChecklistItemNote.is_active.is_(True),
        )
        .options(selectinload(ChecklistItemNote.updated_by_user))
    )
    return res.scalar_one_or_none()


async def fetch_note_with_editor(db: AsyncSession, note_id: int) -> ChecklistItemNote:
    res = await db.execute(
        select(ChecklistItemNote)
        .where(ChecklistItemNote.id == note_id)
        .options(selectinload(ChecklistItemNote.updated_by_user))
    )
    return res.scalar_one()


async def upsert_single(
    db: AsyncSession,
    session_row: Session,
    opportunity_key: str,
    checklist_item_id: int,
    user_id: int,
    note_text: Optional[str],
    influencers_raw: Optional[Sequence[Any]],
    structured_content: Optional[Dict[str, Any]] = None,
    skip_noop: bool = True,
) -> ChecklistItemNote:
    stored_infl = influencers_to_stored(influencers_raw)
    active = await get_active_note(db, checklist_item_id, opportunity_key)
    if skip_noop and active and _content_equal(
        active, note_text, stored_infl, structured_content
    ):
        return active

    if active:
        active.is_active = False
        await db.flush()
        next_version = active.version + 1
        prev_id = active.id
    else:
        next_version = 1
        prev_id = None

    row = ChecklistItemNote(
        checklist_item_id=checklist_item_id,
        session_id=session_row.id,
        customer_name=session_row.customer_name,
        opportunity_name=session_row.opportunity_name,
        opportunity_key=opportunity_key,
        note_text=note_text,
        decision_influencers=stored_infl,
        structured_content=structured_content,
        created_by_user_id=user_id,
        updated_by_user_id=user_id,
        is_active=True,
        version=next_version,
        previous_version_id=prev_id,
    )
    db.add(row)
    await db.flush()
    return await fetch_note_with_editor(db, row.id)


async def bulk_upsert(
    db: AsyncSession,
    session_row: Session,
    opportunity_key: str,
    user_id: int,
    items: List[NoteBulkItemIn],
    skip_noop: bool = True,
) -> NotesBulkUpsertResponse:
    ids = [it.checklist_item_id for it in items]
    await validate_checklist_item_ids(db, ids)

    updated_rows: List[ChecklistItemNote] = []
    for it in items:
        row = await upsert_single(
            db,
            session_row,
            opportunity_key,
            it.checklist_item_id,
            user_id,
            it.note_text,
            it.decision_influencers,
            it.structured_content,
            skip_noop=skip_noop,
        )
        updated_rows.append(row)

    return NotesBulkUpsertResponse(
        session_id=session_row.id,
        customer_name=session_row.customer_name,
        opportunity_name=session_row.opportunity_name,
        opportunity_key=opportunity_key,
        items=[note_to_latest_out(r) for r in updated_rows],
    )


async def list_all_item_ids(db: AsyncSession) -> List[int]:
    res = await db.execute(
        select(ChecklistItem.id)
        .where(ChecklistItem.is_active.is_(True))
        .order_by(ChecklistItem.order)
    )
    return [r[0] for r in res.all()]


async def bundle_latest_for_session(
    db: AsyncSession, session_row: Session, opportunity_key: str
) -> NotesSessionBundleOut:
    item_ids = await list_all_item_ids(db)
    if not item_ids:
        return NotesSessionBundleOut(
            session_id=session_row.id,
            customer_name=session_row.customer_name,
            opportunity_name=session_row.opportunity_name,
            opportunity_key=opportunity_key,
            items=[],
        )

    res = await db.execute(
        select(ChecklistItemNote)
        .where(
            ChecklistItemNote.opportunity_key == opportunity_key,
            ChecklistItemNote.is_active.is_(True),
            ChecklistItemNote.checklist_item_id.in_(item_ids),
        )
        .options(selectinload(ChecklistItemNote.updated_by_user))
    )
    by_item = {r.checklist_item_id: r for r in res.scalars().all()}
    slots = [
        NoteSlotOut(
            checklist_item_id=iid,
            note=note_to_latest_out(by_item[iid]) if iid in by_item else None,
        )
        for iid in item_ids
    ]
    return NotesSessionBundleOut(
        session_id=session_row.id,
        customer_name=session_row.customer_name,
        opportunity_name=session_row.opportunity_name,
        opportunity_key=opportunity_key,
        items=slots,
    )


async def get_latest_for_item(
    db: AsyncSession,
    session_row: Session,
    opportunity_key: str,
    checklist_item_id: int,
) -> Optional[ChecklistItemNote]:
    await validate_checklist_item_ids(db, [checklist_item_id])
    res = await db.execute(
        select(ChecklistItemNote)
        .where(
            ChecklistItemNote.opportunity_key == opportunity_key,
            ChecklistItemNote.checklist_item_id == checklist_item_id,
            ChecklistItemNote.is_active.is_(True),
        )
        .options(selectinload(ChecklistItemNote.updated_by_user))
    )
    return res.scalar_one_or_none()


async def history_for_item(
    db: AsyncSession,
    opportunity_key: str,
    checklist_item_id: int,
) -> List[NoteHistoryEntryOut]:
    await validate_checklist_item_ids(db, [checklist_item_id])
    res = await db.execute(
        select(ChecklistItemNote)
        .where(
            ChecklistItemNote.opportunity_key == opportunity_key,
            ChecklistItemNote.checklist_item_id == checklist_item_id,
        )
        .options(selectinload(ChecklistItemNote.updated_by_user))
        .order_by(ChecklistItemNote.version.asc())
    )
    rows = res.scalars().all()
    return [history_entry_out(r) for r in rows]


async def soft_delete_item(
    db: AsyncSession,
    session_row: Session,
    opportunity_key: str,
    checklist_item_id: int,
    user_id: int,
) -> ChecklistItemNote:
    await validate_checklist_item_ids(db, [checklist_item_id])
    active = await get_active_note(db, checklist_item_id, opportunity_key)
    if not active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active note for this checklist item",
        )
    active.is_active = False
    await db.flush()
    row = ChecklistItemNote(
        checklist_item_id=checklist_item_id,
        session_id=session_row.id,
        customer_name=session_row.customer_name,
        opportunity_name=session_row.opportunity_name,
        opportunity_key=opportunity_key,
        note_text=None,
        decision_influencers=None,
        structured_content=None,
        created_by_user_id=user_id,
        updated_by_user_id=user_id,
        is_active=True,
        version=active.version + 1,
        previous_version_id=active.id,
    )
    db.add(row)
    await db.flush()
    return await fetch_note_with_editor(db, row.id)
