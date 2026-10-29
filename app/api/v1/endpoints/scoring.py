"""
Scoring API endpoints

Read-only views over scores already calculated when a checklist is submitted.
Scores are written by the submit paths in `sessions.py`, not here.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.session import Session
from app.models.checklist import ChecklistItem
from app.models.organization_settings import OrganizationSettings
from app.models.scoring import ScoringResult, ScoreHistory
from app.models.user import User, Organization
from app.api.dependencies import (
    get_current_user,
    get_session_access_filter,
)
from app.services.report_service import build_notes_map_for_pdf, get_report_service
from app.services.s3_service import get_s3_service

logger = logging.getLogger(__name__)

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

@router.get("/{session_id}/score/version/{version_number}/download")
async def download_score_version_report(
    session_id: int,
    version_number: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Download the checklist PDF for one stored score version.

    The PDF uses the same generator and layout as the session report, but is
    rendered from `ScoreHistory.responses_snapshot` rather than from the live
    checklist, so it shows the answers exactly as they were at that version.

    Nothing is persisted: the session's `Report` row holds the current report
    and must not be overwritten by a historical one, so the generated file's
    URL is returned directly.

    RBAC: same read access as viewing the version.
    """
    access_filter = get_session_access_filter(current_user)
    session_result = await db.execute(
        select(Session).where(Session.id == session_id, access_filter)
    )
    session = session_result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or access denied"
        )

    history_result = await db.execute(
        select(ScoreHistory).where(
            ScoreHistory.session_id == session_id,
            ScoreHistory.version_number == version_number,
        )
    )
    history = history_result.scalar_one_or_none()

    if not history:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version {version_number} not found for this session"
        )

    snapshot = history.responses_snapshot or []
    if not snapshot:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This version has no stored checklist answers to export."
        )

    item_ids = [row["item_id"] for row in snapshot]
    items_result = await db.execute(
        select(ChecklistItem)
        .where(ChecklistItem.id.in_(item_ids))
        .options(selectinload(ChecklistItem.category))
    )
    items = {item.id: item for item in items_result.scalars().all()}

    # Shape the snapshot the way generate_session_report() expects. The
    # generator takes plain dicts, so historical values render through exactly
    # the same template as a live report.
    responses_data = []
    raw_points_total = 0
    category_scores: dict = {}

    for row in snapshot:
        item = items.get(row["item_id"])
        if not item or not item.category:
            continue

        answer = row.get("answer")
        item_score = row.get("score") or 0
        raw_points_total += item_score

        bucket = category_scores.setdefault(
            item.category.id,
            {"name": item.category.name, "score": 0, "max_score": 0},
        )
        bucket["max_score"] += 10
        bucket["score"] += item_score

        responses_data.append({
            "id": None,
            "item_id": item.id,
            "is_validated": answer,
            "ai_answer": None,
            "user_answer": answer,
            "confidence": None,
            "evidence_text": None,
            "item": {
                "id": item.id,
                "title": item.title or f"Checklist Item {item.id}",
                "order": getattr(item, "order", item.id),
                "definition": getattr(item, "definition", "") or "",
                "category": {
                    "id": item.category.id,
                    "name": item.category.name or "Uncategorized",
                },
            },
        })

    responses_data.sort(key=lambda row: row["item"]["order"])
    max_possible_score = len(responses_data) * 10

    org_logo_url = None
    org_name = None
    owner_result = await db.execute(select(User).where(User.id == session.user_id))
    session_owner = owner_result.scalar_one_or_none()
    if session_owner and session_owner.organization_id:
        org_result = await db.execute(
            select(Organization).where(
                Organization.id == session_owner.organization_id
            )
        )
        organization = org_result.scalar_one_or_none()
        if organization:
            org_name = organization.name
        settings_result = await db.execute(
            select(OrganizationSettings).where(
                OrganizationSettings.organization_id == session_owner.organization_id
            )
        )
        org_settings = settings_result.scalar_one_or_none()
        if org_settings and org_settings.logo_url:
            org_logo_url = org_settings.logo_url.strip() or None

    risk_band = (
        history.risk_band.value
        if hasattr(history.risk_band, "value")
        else history.risk_band
    )

    session_data = {
        "customer_name": session.customer_name,
        "opportunity_name": session.opportunity_name,
        "deal_stage": session.deal_stage,
        "created_at": session.created_at,
        # The version's own timestamp, not "now": this document reports on a
        # point in history.
        "review_generated_at": history.calculated_at,
    }

    scoring_data = {
        "total_score": history.total_score,
        "risk_band": risk_band,
        "category_scores": category_scores,
        "top_strengths": [],
        "top_gaps": [],
        "items_validated": history.items_validated,
        "items_total": history.items_total,
        "raw_points_total": raw_points_total,
        "max_raw_points": max_possible_score,
    }

    # Notes are not versioned, so the current notes are the only ones available.
    notes_by_item_id = await build_notes_map_for_pdf(db, session)

    report_service = get_report_service()
    try:
        pdf_result = await report_service.generate_session_report(
            session_id=session_id,
            user_id=current_user.id,
            session_data=session_data,
            scoring_data=scoring_data,
            coaching_data=None,
            responses_data=responses_data,
            organization_logo_url=org_logo_url,
            organization_name=org_name,
            notes_by_item_id=notes_by_item_id,
        )
    except Exception as exc:  # noqa: BLE001 - surfaced to the caller, logged for us
        logger.error(
            "Failed to generate version %s report for session %s: %s",
            version_number, session_id, exc, exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate the report for this version."
        ) from exc

    # The reports bucket is private, so the plain object URL in `pdf_url` is
    # rejected with AccessDenied. Sign it the same way the session report
    # download does.
    download_url = pdf_result.get("pdf_url")
    s3_bucket = pdf_result.get("s3_bucket")
    s3_key = pdf_result.get("s3_key")

    if s3_bucket and s3_key:
        try:
            presigned_url = get_s3_service().generate_presigned_url(
                s3_key,
                expiration=3600,
                bucket_name=s3_bucket,
            )
            if presigned_url:
                download_url = presigned_url
            else:
                logger.error(
                    "Presigned URL came back empty for version report "
                    "(bucket=%s, key=%s)", s3_bucket, s3_key,
                )
        except Exception as exc:  # noqa: BLE001 - fall back to the raw URL
            logger.error(
                "Failed to presign version report URL (bucket=%s, key=%s): %s",
                s3_bucket, s3_key, exc, exc_info=True,
            )

    if not download_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate download URL"
        )

    return {
        "session_id": session_id,
        "version_number": version_number,
        "download_url": download_url,
        "file_size": pdf_result.get("file_size"),
        "filename": f"sales_checklist_session_{session_id}_version_{version_number}.pdf",
    }
