"""
Coaching Report API — leader, team, and individual salesperson views.
"""
import logging
from datetime import date, datetime
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.api.v1.endpoints.manager_dashboard import can_view_team_data, get_team_members
from app.core.dashboard_date import get_dashboard_date_range
from app.db.session import get_db
from app.models.checklist import ChecklistItem
from app.models.session import Session, SessionResponse
from app.models.user import User
from app.services.coaching_report_service import build_coaching_report_overview

router = APIRouter()
logger = logging.getLogger(__name__)


class CoachingReportKpis(BaseModel):
    active_checklists: int
    coaching_opportunities: int
    blank_answers: int
    lost_deals_to_review: int
    gaps_closed: int
    won_count: int
    lost_count: int


class ChecklistItemSummary(BaseModel):
    id: int
    order: int
    title: str
    coaching_text: str


class GridItemCell(BaseModel):
    item_id: int
    order: int
    status: Literal["yes", "gap", "blank"]


class GridRow(BaseModel):
    session_id: int
    salesperson_id: int
    salesperson_name: str
    customer_name: str
    opportunity_name: str
    days_active: int
    deal_stage: Optional[str] = None
    score: Optional[float] = None
    items: List[GridItemCell]
    yes_count: int
    gap_count: int
    blank_count: int
    coaching_note_id: Optional[int] = None
    coaching_note_text: Optional[str] = None
    coaching_note_count: int = 0
    critical_gap_item_id: Optional[int] = None
    critical_gap_title: Optional[str] = None
    recommended_action: Optional[str] = None


class CommonGap(BaseModel):
    item_id: int
    item_order: int
    title: str
    missing_count: int
    total_sessions: int
    gap_percentage: float
    coaching_text: str


class SalespersonPriority(BaseModel):
    salesperson_id: int
    salesperson_name: str
    session_count: int
    proficiency: float
    gap_count: int
    yes_count: int
    blank_count: int
    lowest_gap_item_id: Optional[int] = None
    lowest_gap_title: Optional[str] = None
    lowest_gap_count: int = 0
    coaching_text: Optional[str] = None


class PriorityOpportunity(BaseModel):
    session_id: int
    salesperson_id: int
    salesperson_name: str
    customer_name: str
    opportunity_name: str
    score: Optional[float] = None
    gap_count: int
    priority: Literal["critical", "high", "watch"]
    critical_gap_title: Optional[str] = None
    recommended_action: Optional[str] = None


class ClosedDeal(BaseModel):
    session_id: int
    salesperson_id: int
    salesperson_name: str
    customer_name: str
    opportunity_name: str
    missing_count: int
    present_count: int
    score: Optional[float] = None
    deal_stage: Optional[str] = None


class SalespersonOption(BaseModel):
    id: int
    name: str


class GapClosedEvent(BaseModel):
    session_id: int
    salesperson_id: int
    salesperson_name: str
    customer_name: str
    opportunity_name: str
    item_id: int
    item_order: int
    item_title: str
    sales_behavior_performed: str
    coaching_provided: Optional[str] = None
    closed_at: datetime


class WeeklyTrendPoint(BaseModel):
    week_start: str
    label: str
    average_score: Optional[float] = None
    gaps_closed: int
    session_count: int


class OutcomePattern(BaseModel):
    item_id: int
    item_order: int
    title: str
    percentage: float


class NextBehavior(BaseModel):
    item_id: int
    item_order: int
    title: str
    coaching_text: str


class CoachingReportOverview(BaseModel):
    kpis: CoachingReportKpis
    checklist_items: List[ChecklistItemSummary]
    grid_rows: List[GridRow]
    common_gaps: List[CommonGap]
    salesperson_priorities: List[SalespersonPriority]
    priority_opportunities: List[PriorityOpportunity]
    lost_deals: List[ClosedDeal]
    won_deals: List[ClosedDeal]
    salespeople: List[SalespersonOption]
    gaps_closed_events: List[GapClosedEvent]
    weekly_trend: List[WeeklyTrendPoint]
    win_patterns: List[OutcomePattern]
    lose_patterns: List[OutcomePattern]
    next_behavior_to_coach: Optional[NextBehavior] = None


class EvidenceStatusUpdate(BaseModel):
    status: Literal["yes", "gap", "blank"]


class EvidenceStatusUpdateResponse(BaseModel):
    session_id: int
    item_id: int
    status: Literal["yes", "gap", "blank"]
    message: str


@router.get("/overview", response_model=CoachingReportOverview)
async def get_coaching_report_overview(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    start_date: Optional[date] = Query(
        None,
        description="Range start (UTC). Defaults to the first day of the current month.",
    ),
    end_date: Optional[date] = Query(
        None,
        description="Range end (UTC). Defaults to today.",
    ),
):
    """
    One payload for Sales Leader, Sales Team, and Individual views.

    **Permissions:**
    - MANAGER: team scope
    - ADMIN: organization scope
    - SYSTEM_ADMIN: all
    """
    if not can_view_team_data(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only managers and admins can access the coaching report",
        )

    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be on or before end_date",
        )

    team_member_ids = await get_team_members(current_user, db)
    range_start, range_end, _, _ = get_dashboard_date_range(start_date, end_date)

    try:
        payload = await build_coaching_report_overview(
            db=db,
            team_member_ids=team_member_ids,
            range_start=range_start,
            range_end=range_end,
        )
    except Exception:
        logger.exception(
            "Failed to build coaching report overview for user %s",
            current_user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not load the coaching report. Please try again.",
        )
    logger.info(
        "Coaching report overview for user %s: %s active checklists",
        current_user.id,
        payload["kpis"]["active_checklists"],
    )
    return payload


@router.put(
    "/sessions/{session_id}/items/{item_id}",
    response_model=EvidenceStatusUpdateResponse,
)
async def update_team_evidence_status(
    session_id: int,
    item_id: int,
    payload: EvidenceStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create, update, or clear a checklist answer from the team evidence grid."""
    if not can_view_team_data(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only managers and admins can update coaching evidence.",
        )

    team_member_ids = await get_team_members(current_user, db)
    session = await db.get(Session, session_id)
    if session is None or session.user_id not in team_member_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    item = await db.get(ChecklistItem, item_id)
    if item is None or not item.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Checklist item not found",
        )

    result = await db.execute(
        select(SessionResponse).where(
            SessionResponse.session_id == session_id,
            SessionResponse.item_id == item_id,
        )
    )
    response = result.scalar_one_or_none()

    if payload.status == "blank":
        if response is not None:
            await db.delete(response)
            await db.commit()
        return EvidenceStatusUpdateResponse(
            session_id=session_id,
            item_id=item_id,
            status="blank",
            message="Checklist item cleared",
        )

    answer = payload.status == "yes"
    if response is None:
        response = SessionResponse(
            session_id=session_id,
            item_id=item_id,
            ai_answer=answer,
            ai_reasoning="Updated from coaching report",
            user_answer=answer,
            was_changed=False,
            score=10 if answer else 0,
        )
        db.add(response)
    else:
        response.user_answer = answer
        response.was_changed = response.user_answer != response.ai_answer
        final_answer = (
            response.user_answer
            if response.user_answer is not None
            else response.ai_answer
        )
        response.score = 10 if final_answer else 0

    await db.commit()
    return EvidenceStatusUpdateResponse(
        session_id=session_id,
        item_id=item_id,
        status=payload.status,
        message="Checklist item updated successfully",
    )
