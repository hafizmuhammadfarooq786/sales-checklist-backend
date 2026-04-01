"""
Checklist item notes — opportunity-scoped, session-addressable API.
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.api.dependencies import get_current_active_user, check_session_access
from app.schemas.notes import (
    NoteItemSingleOut,
    NoteLatestOut,
    NoteUpsertBody,
    NotesBulkUpsertRequest,
    NotesBulkUpsertResponse,
    NotesSessionBundleOut,
    NoteHistoryEntryOut,
)
from app.services.notes_service import (
    bulk_upsert,
    bundle_latest_for_session,
    compute_opportunity_key,
    history_for_item,
    load_session_for_notes,
    get_latest_for_item,
    note_to_latest_out,
    delete_note_version,
    soft_delete_item,
    update_note_version,
    upsert_single,
)

router = APIRouter()


async def _require_session_notes_access(
    session_id: int,
    current_user: User,
    db: AsyncSession,
):
    if not await check_session_access(session_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    session_row = await load_session_for_notes(db, session_id)
    if not session_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    key = compute_opportunity_key(session_row.customer_name, session_row.opportunity_name)
    return session_row, key


@router.get("/sessions/{session_id}", response_model=NotesSessionBundleOut)
async def get_notes_for_session(
    session_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    session_row, key = await _require_session_notes_access(session_id, current_user, db)
    return await bundle_latest_for_session(db, session_row, key)


@router.put("/sessions/{session_id}/bulk", response_model=NotesBulkUpsertResponse)
async def bulk_save_notes(
    session_id: int,
    body: NotesBulkUpsertRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    session_row, key = await _require_session_notes_access(session_id, current_user, db)
    return await bulk_upsert(db, session_row, key, current_user.id, body.items)


@router.put("/sessions/{session_id}/items/{checklist_item_id}", response_model=NoteLatestOut)
async def upsert_one_note(
    session_id: int,
    checklist_item_id: int,
    body: NoteUpsertBody,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    session_row, key = await _require_session_notes_access(session_id, current_user, db)
    row = await upsert_single(
        db,
        session_row,
        key,
        checklist_item_id,
        current_user.id,
        body.note_text,
        body.decision_influencers,
        body.structured_content,
    )
    return note_to_latest_out(row)


@router.get(
    "/sessions/{session_id}/items/{checklist_item_id}",
    response_model=NoteItemSingleOut,
)
async def get_one_note_latest(
    session_id: int,
    checklist_item_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    session_row, key = await _require_session_notes_access(session_id, current_user, db)
    row = await get_latest_for_item(db, session_row, key, checklist_item_id)
    return NoteItemSingleOut(
        checklist_item_id=checklist_item_id,
        note=note_to_latest_out(row) if row else None,
    )


@router.get(
    "/sessions/{session_id}/items/{checklist_item_id}/history",
    response_model=List[NoteHistoryEntryOut],
)
async def get_note_history(
    session_id: int,
    checklist_item_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    session_row, key = await _require_session_notes_access(session_id, current_user, db)
    _ = session_row  # access already validated
    return await history_for_item(db, key, checklist_item_id)


@router.delete(
    "/sessions/{session_id}/items/{checklist_item_id}",
    response_model=NoteItemSingleOut,
)
async def soft_clear_note(
    session_id: int,
    checklist_item_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    session_row, key = await _require_session_notes_access(session_id, current_user, db)
    row = await soft_delete_item(
        db, session_row, key, checklist_item_id, current_user.id
    )
    return NoteItemSingleOut(
        checklist_item_id=checklist_item_id,
        note=note_to_latest_out(row) if row else None,
    )


@router.put(
    "/sessions/{session_id}/items/{checklist_item_id}/history/{note_id}",
    response_model=NoteLatestOut,
)
async def edit_history_note(
    session_id: int,
    checklist_item_id: int,
    note_id: int,
    body: NoteUpsertBody,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    _session_row, key = await _require_session_notes_access(session_id, current_user, db)
    row = await update_note_version(
        db,
        key,
        checklist_item_id,
        note_id,
        current_user.id,
        body.note_text,
        body.decision_influencers,
        body.structured_content,
    )
    return note_to_latest_out(row)


@router.delete(
    "/sessions/{session_id}/items/{checklist_item_id}/history/{note_id}",
    response_model=NoteItemSingleOut,
)
async def delete_history_note(
    session_id: int,
    checklist_item_id: int,
    note_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    _session_row, key = await _require_session_notes_access(session_id, current_user, db)
    row = await delete_note_version(
        db, key, checklist_item_id, note_id, current_user.id
    )
    return NoteItemSingleOut(
        checklist_item_id=checklist_item_id,
        note=note_to_latest_out(row) if row else None,
    )
