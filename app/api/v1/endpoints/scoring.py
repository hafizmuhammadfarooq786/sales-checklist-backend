"""
Scoring API endpoints

Read-only views over scores already calculated when a checklist is submitted.
Scores are written by the submit paths in `sessions.py`, not here.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.session import Session
from app.models.checklist import ChecklistItem
from app.models.scoring import ScoringResult, ScoreHistory
from app.models.user import User
from app.api.dependencies import (
    get_current_user,
    get_session_access_filter,
)

router = APIRouter()


@router.get("/{session_id}/score")
async def get_session_score(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get existing score for a session

    RBAC:
    - REP: Can view own sessions
    - MANAGER: Can view team sessions
    - ADMIN: Can view org sessions
    - SYSTEM_ADMIN: Can view all sessions
    """
    # Verify session access with RBAC
    access_filter = get_session_access_filter(current_user)
    session_result = await db.execute(
        select(Session).where(
            Session.id == session_id,
            access_filter
        )
    )
    session = session_result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or access denied"
        )

    # Get scoring result
    scoring_result = await db.execute(
        select(ScoringResult).where(ScoringResult.session_id == session_id)
    )
    result = scoring_result.scalar_one_or_none()

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Score not calculated yet. Use POST /calculate to generate score."
        )

    return {
        "session_id": session_id,
        "total_score": result.total_score,
        "max_possible_score": 100,
        "percentage": result.total_score,
        "risk_band": result.risk_band,
        "validated_items_count": result.items_validated,
        "unvalidated_items_count": result.items_total - result.items_validated,
        "strengths_summary": ", ".join(result.top_strengths) if result.top_strengths else "",
        "gaps_summary": ", ".join(result.top_gaps) if result.top_gaps else "",
        "created_at": result.created_at,
        "scoring_result_id": result.id
    }


@router.get("/{session_id}/score/history")
async def get_score_history(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get complete score history for a session.
    Returns all score calculations ordered by most recent first.
    Includes score changes, trigger events, and timestamps.

    RBAC:
    - REP: Can view own sessions
    - MANAGER: Can view team sessions
    - ADMIN: Can view org sessions
    - SYSTEM_ADMIN: Can view all sessions
    """
    # Verify session access with RBAC
    access_filter = get_session_access_filter(current_user)
    session_result = await db.execute(
        select(Session).where(
            Session.id == session_id,
            access_filter
        )
    )
    session = session_result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or access denied"
        )

    # Get all score history for this session, ordered by most recent first
    history_result = await db.execute(
        select(ScoreHistory)
        .where(ScoreHistory.session_id == session_id)
        .order_by(ScoreHistory.calculated_at.desc())
    )
    history_records = history_result.scalars().all()

    if not history_records:
        return {
            "session_id": session_id,
            "customer_name": session.customer_name,
            "history": [],
            "total_calculations": 0,
            "message": "No score history found. Calculate a score first."
        }

    # Format history records for response
    formatted_history = []
    for record in history_records:
        formatted_history.append({
            "id": record.id,
            "total_score": record.total_score,
            "risk_band": record.risk_band,
            "items_validated": record.items_validated,
            "items_total": record.items_total,
            "calculated_at": record.calculated_at.isoformat(),
            "score_change": record.score_change,
            "trigger_event": record.trigger_event,
            "created_by_user_id": record.created_by_user_id
        })

    # Calculate summary statistics
    latest_score = history_records[0].total_score
    oldest_score = history_records[-1].total_score
    total_improvement = latest_score - oldest_score if len(history_records) > 1 else 0

    return {
        "session_id": session_id,
        "customer_name": session.customer_name,
        "history": formatted_history,
        "total_calculations": len(history_records),
        "summary": {
            "latest_score": latest_score,
            "oldest_score": oldest_score,
            "total_improvement": total_improvement,
            "latest_risk_band": history_records[0].risk_band,
            "first_calculated": history_records[-1].calculated_at.isoformat(),
            "last_calculated": history_records[0].calculated_at.isoformat()
        }
    }


@router.get("/{session_id}/score/version/{version_number}")
async def get_score_version_details(
    session_id: int,
    version_number: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get complete details for a specific score version.

    Returns:
    - Score and risk band at that version
    - Complete checklist state (all 92 responses)
    - Metadata about changes from previous version

    This allows users to view exactly what the checklist looked like
    at any point in history.

    RBAC:
    - REP: Can view own sessions
    - MANAGER: Can view team sessions
    - ADMIN: Can view org sessions
    - SYSTEM_ADMIN: Can view all sessions
    """
    # Verify session access with RBAC
    access_filter = get_session_access_filter(current_user)
    session_result = await db.execute(
        select(Session).where(
            Session.id == session_id,
            access_filter
        )
    )
    session = session_result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or access denied"
        )

    # Get the specific version from score history
    history_result = await db.execute(
        select(ScoreHistory)
        .where(
            ScoreHistory.session_id == session_id,
            ScoreHistory.version_number == version_number
        )
    )
    history = history_result.scalar_one_or_none()

    if not history:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version {version_number} not found for this session"
        )

    # Get checklist item details for the responses in this version
    item_ids = [r["item_id"] for r in history.responses_snapshot]
    items_result = await db.execute(
        select(ChecklistItem)
        .where(ChecklistItem.id.in_(item_ids))
        .options(selectinload(ChecklistItem.category))
    )
    items = {item.id: item for item in items_result.scalars().all()}

    # Build detailed checklist items with category information
    checklist_items = []
    for response_data in history.responses_snapshot:
        item_id = response_data["item_id"]
        item = items.get(item_id)

        if item:
            checklist_items.append({
                "item_id": item_id,
                "title": item.title,
                "definition": item.definition,
                "category": item.category.name if item.category else None,
                "order": item.order,
                "answer": response_data["answer"],
                "score": response_data["score"]
            })

    # Sort by order
    checklist_items.sort(key=lambda x: x.get("order", 0))

    return {
        "session_id": session_id,
        "customer_name": session.customer_name,
        "opportunity_name": session.opportunity_name,
        "version": {
            "version_number": history.version_number,
            "total_score": history.total_score,
            "risk_band": history.risk_band,
            "items_validated": history.items_validated,
            "items_total": history.items_total,
            "calculated_at": history.calculated_at.isoformat(),
            "score_change": history.score_change,
            "changes_count": history.changes_count,
            "trigger_event": history.trigger_event,
            "created_by_user_id": history.created_by_user_id
        },
        "checklist_items": checklist_items
    }