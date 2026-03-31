"""
Manager Dashboard API endpoints
Provides analytics, notifications, and team insights for managers
"""
import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, case, desc
from sqlalchemy.orm import selectinload, joinedload
from typing import List, Optional
from pydantic import BaseModel

from app.db.session import get_db
from app.models.session import Session, SessionResponse, SessionStatus, DealStage
from app.models.scoring import ScoringResult
from app.models.user import User, UserRole
from app.models.checklist import ChecklistItem, ChecklistCategory
from app.api.dependencies import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)


# Response Models
class DealAlert(BaseModel):
    """Alert for at-risk or notable deals"""
    session_id: int
    customer_name: str
    salesperson_name: str
    salesperson_id: int
    alert_type: str  # "stalled", "at_risk", "high_score_lost"
    score: Optional[int] = None
    days_inactive: Optional[int] = None
    deal_stage: Optional[str] = None
    last_updated: datetime

    class Config:
        from_attributes = True


class MissingItemAnalysis(BaseModel):
    """Analysis of frequently missing checklist items"""
    item_id: int
    item_text: str
    category_name: str
    missing_count: int
    total_sessions: int
    missing_percentage: float

    class Config:
        from_attributes = True


class SalespersonNoReport(BaseModel):
    """Individual salesperson's 'No' responses report"""
    salesperson_id: int
    salesperson_name: str
    total_sessions: int
    total_no_responses: int
    no_percentage: float
    missing_items: List[MissingItemAnalysis]

    class Config:
        from_attributes = True


class TeamNoSummary(BaseModel):
    """Team-wide summary of 'No' responses"""
    total_sessions: int
    total_responses: int
    total_no_responses: int
    no_percentage: float
    top_missing_items: List[MissingItemAnalysis]

    class Config:
        from_attributes = True


class ActiveChecklist(BaseModel):
    """Active checklist summary"""
    session_id: int
    customer_name: str
    opportunity_name: str
    salesperson_name: str
    salesperson_id: int
    score: Optional[int] = None
    status: str
    deal_stage: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DashboardNotifications(BaseModel):
    """Dashboard notifications summary"""
    stalled_deals: List[DealAlert]
    at_risk_deals: List[DealAlert]
    high_score_lost_deals: List[DealAlert]
    total_alerts: int

    class Config:
        from_attributes = True


class DashboardStats(BaseModel):
    """Overall dashboard statistics"""
    total_active_checklists: int
    total_team_members: int
    average_team_score: Optional[float] = None
    total_alerts: int

    class Config:
        from_attributes = True


class TeamTrainingGaps(BaseModel):
    """Team training gaps summary"""
    top_missing_items: List[MissingItemAnalysis]

    class Config:
        from_attributes = True


class ManagerDashboardOverview(BaseModel):
    """Complete manager dashboard overview"""
    stats: DashboardStats
    notifications: DashboardNotifications
    active_checklists: List[ActiveChecklist]
    team_training_gaps: TeamTrainingGaps

    class Config:
        from_attributes = True


# Helper Functions
def can_view_team_data(user: User) -> bool:
    """Check if user can view team data (Manager or Admin)"""
    return user.role in [UserRole.MANAGER, UserRole.ADMIN, UserRole.SYSTEM_ADMIN]


async def get_team_members(user: User, db: AsyncSession) -> List[int]:
    """Get list of team member IDs based on user's role"""
    if user.role == UserRole.SYSTEM_ADMIN:
        # System admin sees all users
        result = await db.execute(select(User.id))
        return [row[0] for row in result.all()]

    elif user.role == UserRole.ADMIN:
        # Org admin sees all users in their organization
        result = await db.execute(
            select(User.id).where(User.organization_id == user.organization_id)
        )
        return [row[0] for row in result.all()]

    elif user.role == UserRole.MANAGER:
        # Manager sees users in their team
        result = await db.execute(
            select(User.id).where(User.team_id == user.team_id)
        )
        return [row[0] for row in result.all()]

    else:
        # Reps only see themselves
        return [user.id]


# Endpoints

@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get overall dashboard statistics

    **Permissions:**
    - MANAGER: Team statistics
    - ADMIN: Organization statistics
    - SYSTEM_ADMIN: All statistics
    """
    if not can_view_team_data(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only managers and admins can access dashboard statistics"
        )

    team_member_ids = await get_team_members(current_user, db)

    # Count active checklists
    active_result = await db.execute(
        select(func.count(Session.id)).where(
            and_(
                Session.user_id.in_(team_member_ids),
                Session.status.in_([
                    SessionStatus.PENDING_REVIEW,
                    SessionStatus.COMPLETED
                ])
            )
        )
    )
    total_active = active_result.scalar() or 0

    # Average team score
    score_result = await db.execute(
        select(func.avg(ScoringResult.total_score)).where(
            and_(
                ScoringResult.session_id == Session.id,
                Session.user_id.in_(team_member_ids)
            )
        )
    )
    avg_score = score_result.scalar()

    # Count alerts
    stalled_count = await db.execute(
        select(func.count(Session.id)).where(
            and_(
                Session.user_id.in_(team_member_ids),
                Session.updated_at < datetime.utcnow() - timedelta(days=30),
                Session.status != SessionStatus.COMPLETED
            )
        )
    )

    at_risk_count = await db.execute(
        select(func.count(Session.id)).where(
            and_(
                Session.user_id.in_(team_member_ids),
                Session.id == ScoringResult.session_id,
                ScoringResult.total_score <= 30
            )
        )
    )

    total_alerts = (stalled_count.scalar() or 0) + (at_risk_count.scalar() or 0)

    return DashboardStats(
        total_active_checklists=total_active,
        total_team_members=len(team_member_ids),
        average_team_score=round(avg_score / 5) * 5 if avg_score else None,
        total_alerts=total_alerts
    )


@router.get("/notifications", response_model=DashboardNotifications)
async def get_dashboard_notifications(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get dashboard notifications and alerts

    Returns:
    - Stalled deals (no activity for 30+ days)
    - At-risk deals (scores 0-30)
    - High-scoring lost deals (70+ but lost/no decision)

    **Permissions:**
    - MANAGER: Team notifications
    - ADMIN: Organization notifications
    - SYSTEM_ADMIN: All notifications
    """
    if not can_view_team_data(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only managers and admins can access notifications"
        )

    team_member_ids = await get_team_members(current_user, db)

    # Stalled deals (30+ days inactive)
    stalled_result = await db.execute(
        select(Session, User, ScoringResult).where(
            and_(
                Session.user_id.in_(team_member_ids),
                Session.updated_at < datetime.utcnow() - timedelta(days=30),
                Session.status != SessionStatus.COMPLETED,
                Session.user_id == User.id
            )
        ).outerjoin(ScoringResult, Session.id == ScoringResult.session_id)
        .order_by(Session.updated_at.asc())
        .limit(50)
    )

    stalled_deals = []
    for session, user, scoring in stalled_result:
        days_inactive = (datetime.utcnow() - session.updated_at).days
        stalled_deals.append(DealAlert(
            session_id=session.id,
            customer_name=session.customer_name,
            salesperson_name=f"{user.first_name or ''} {user.last_name or ''}".strip() or user.email,
            salesperson_id=user.id,
            alert_type="stalled",
            score=scoring.total_score if scoring else None,
            days_inactive=days_inactive,
            deal_stage=session.deal_stage,
            last_updated=session.updated_at
        ))

    # At-risk deals (scores 0-30)
    at_risk_result = await db.execute(
        select(Session, User, ScoringResult).where(
            and_(
                Session.user_id.in_(team_member_ids),
                Session.id == ScoringResult.session_id,
                ScoringResult.total_score <= 30,
                Session.user_id == User.id
            )
        ).order_by(ScoringResult.total_score.asc())
        .limit(50)
    )

    at_risk_deals = []
    for session, user, scoring in at_risk_result:
        at_risk_deals.append(DealAlert(
            session_id=session.id,
            customer_name=session.customer_name,
            salesperson_name=f"{user.first_name or ''} {user.last_name or ''}".strip() or user.email,
            salesperson_id=user.id,
            alert_type="at_risk",
            score=scoring.total_score,
            deal_stage=session.deal_stage,
            last_updated=session.updated_at
        ))

    # High-scoring lost deals (70+ but lost/no decision/disengaged)
    # Try with DISENGAGED first, fallback to just LOST and NO_DECISION if enum doesn't have DISENGAGED yet
    try:
        high_score_lost_result = await db.execute(
            select(Session, User, ScoringResult).where(
                and_(
                    Session.user_id.in_(team_member_ids),
                    Session.id == ScoringResult.session_id,
                    ScoringResult.total_score >= 70,
                    Session.deal_stage.in_([DealStage.LOST, DealStage.NO_DECISION, DealStage.DISENGAGED]),
                    Session.user_id == User.id
                )
            ).order_by(desc(ScoringResult.total_score))
            .limit(50)
        )
    except Exception as e:
        # If DISENGAGED is not in the database enum yet, rollback and query without it
        if "DISENGAGED" in str(e) or "disengaged" in str(e) or "InFailedSQLTransactionError" in str(e):
            logger.warning("DISENGAGED enum value not found in database, querying without it. Run migration 0090406d8bf9.")
            # Rollback the failed transaction before retrying
            await db.rollback()
            high_score_lost_result = await db.execute(
                select(Session, User, ScoringResult).where(
                    and_(
                        Session.user_id.in_(team_member_ids),
                        Session.id == ScoringResult.session_id,
                        ScoringResult.total_score >= 70,
                        Session.deal_stage.in_([DealStage.LOST, DealStage.NO_DECISION]),
                        Session.user_id == User.id
                    )
                ).order_by(desc(ScoringResult.total_score))
                .limit(50)
            )
        else:
            raise

    high_score_lost_deals = []
    for session, user, scoring in high_score_lost_result:
        high_score_lost_deals.append(DealAlert(
            session_id=session.id,
            customer_name=session.customer_name,
            salesperson_name=f"{user.first_name or ''} {user.last_name or ''}".strip() or user.email,
            salesperson_id=user.id,
            alert_type="high_score_lost",
            score=scoring.total_score,
            deal_stage=session.deal_stage,
            last_updated=session.updated_at
        ))

    total_alerts = len(stalled_deals) + len(at_risk_deals) + len(high_score_lost_deals)

    return DashboardNotifications(
        stalled_deals=stalled_deals,
        at_risk_deals=at_risk_deals,
        high_score_lost_deals=high_score_lost_deals,
        total_alerts=total_alerts
    )


@router.get("/active-checklists", response_model=List[ActiveChecklist])
async def get_active_checklists(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    sort_by: str = Query("updated_at", regex="^(updated_at|created_at|score|salesperson)$"),
    order: str = Query("desc", regex="^(asc|desc)$")
):
    """
    Get list of all active checklists with sorting

    **Query Parameters:**
    - sort_by: Field to sort by (updated_at, created_at, score, salesperson)
    - order: Sort order (asc, desc)

    **Permissions:**
    - MANAGER: Team checklists
    - ADMIN: Organization checklists
    - SYSTEM_ADMIN: All checklists
    """
    if not can_view_team_data(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only managers and admins can access team checklists"
        )

    team_member_ids = await get_team_members(current_user, db)

    # Build query
    query = (
        select(Session, User, ScoringResult)
        .where(
            and_(
                Session.user_id.in_(team_member_ids),
                Session.status.in_([
                    SessionStatus.PENDING_REVIEW,
                    SessionStatus.COMPLETED
                ]),
                Session.user_id == User.id
            )
        )
        .outerjoin(ScoringResult, Session.id == ScoringResult.session_id)
    )

    # Apply sorting
    if sort_by == "updated_at":
        query = query.order_by(desc(Session.updated_at) if order == "desc" else Session.updated_at)
    elif sort_by == "created_at":
        query = query.order_by(desc(Session.created_at) if order == "desc" else Session.created_at)
    elif sort_by == "score":
        query = query.order_by(desc(ScoringResult.total_score) if order == "desc" else ScoringResult.total_score)
    elif sort_by == "salesperson":
        query = query.order_by(desc(User.email) if order == "desc" else User.email)

    result = await db.execute(query)

    active_checklists = []
    for session, user, scoring in result:
        active_checklists.append(ActiveChecklist(
            session_id=session.id,
            customer_name=session.customer_name,
            opportunity_name=session.opportunity_name,
            salesperson_name=f"{user.first_name or ''} {user.last_name or ''}".strip() or user.email,
            salesperson_id=user.id,
            score=scoring.total_score if scoring else None,
            status=session.status.value,
            deal_stage=session.deal_stage,
            created_at=session.created_at,
            updated_at=session.updated_at
        ))

    return active_checklists


@router.get("/training-gaps/salesperson/{salesperson_id}", response_model=SalespersonNoReport)
async def get_salesperson_no_report(
    salesperson_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get individual salesperson's 'No' responses report

    Shows:
    - Total sessions
    - Total 'No' responses
    - Percentage of 'No' responses
    - List of frequently missing items

    **Permissions:**
    - MANAGER: Can view team members
    - ADMIN: Can view organization members
    - SYSTEM_ADMIN: Can view all
    """
    if not can_view_team_data(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only managers and admins can access training gap analysis"
        )

    team_member_ids = await get_team_members(current_user, db)

    if salesperson_id not in team_member_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view this salesperson's data"
        )

    # Get salesperson info
    salesperson = await db.get(User, salesperson_id)
    if not salesperson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salesperson not found"
        )

    # Get total sessions count
    total_sessions_result = await db.execute(
        select(func.count(Session.id)).where(Session.user_id == salesperson_id)
    )
    total_sessions = total_sessions_result.scalar() or 0

    # Get total responses and No responses
    responses_result = await db.execute(
        select(
            func.count(SessionResponse.id).label('total_responses'),
            func.sum(case((SessionResponse.ai_answer == False, 1), else_=0)).label('no_responses')
        ).where(
            and_(
                SessionResponse.session_id == Session.id,
                Session.user_id == salesperson_id
            )
        )
    )
    responses_data = responses_result.first()
    total_responses = responses_data.total_responses or 0
    total_no_responses = responses_data.no_responses or 0

    # Get missing items analysis
    missing_items_result = await db.execute(
        select(
            ChecklistItem.id,
            ChecklistItem.title.label('item_text'),
            ChecklistCategory.name.label('category_name'),
            func.count(SessionResponse.id).label('missing_count')
        ).join(
            ChecklistCategory, ChecklistItem.category_id == ChecklistCategory.id
        ).where(
            and_(
                SessionResponse.session_id == Session.id,
                Session.user_id == salesperson_id,
                SessionResponse.item_id == ChecklistItem.id,
                SessionResponse.ai_answer == False
            )
        ).group_by(ChecklistItem.id, ChecklistItem.title, ChecklistCategory.name)
        .order_by(desc(func.count(SessionResponse.id)))
        .limit(10)
    )

    missing_items = []
    for item_id, item_text, category_name, missing_count in missing_items_result:
        missing_percentage = (missing_count / total_sessions * 100) if total_sessions > 0 else 0
        missing_items.append(MissingItemAnalysis(
            item_id=item_id,
            item_text=item_text,
            category_name=category_name,
            missing_count=missing_count,
            total_sessions=total_sessions,
            missing_percentage=round(missing_percentage, 1)
        ))

    no_percentage = (total_no_responses / total_responses * 100) if total_responses > 0 else 0

    return SalespersonNoReport(
        salesperson_id=salesperson_id,
        salesperson_name=f"{salesperson.first_name or ''} {salesperson.last_name or ''}".strip() or salesperson.email,
        total_sessions=total_sessions,
        total_no_responses=total_no_responses,
        no_percentage=round(no_percentage, 1),
        missing_items=missing_items
    )


@router.get("/training-gaps/team", response_model=TeamNoSummary)
async def get_team_no_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get team-wide summary of 'No' responses

    Shows:
    - Total team sessions
    - Total team 'No' responses
    - Team 'No' percentage
    - Top 3 most frequently missing items (risk drivers)

    **Permissions:**
    - MANAGER: Team summary
    - ADMIN: Organization summary
    - SYSTEM_ADMIN: All summary
    """
    if not can_view_team_data(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only managers and admins can access team training gaps"
        )

    team_member_ids = await get_team_members(current_user, db)

    # Get total sessions count
    total_sessions_result = await db.execute(
        select(func.count(Session.id)).where(Session.user_id.in_(team_member_ids))
    )
    total_sessions = total_sessions_result.scalar() or 0

    # Get total responses and No responses
    responses_result = await db.execute(
        select(
            func.count(SessionResponse.id).label('total_responses'),
            func.sum(case((SessionResponse.ai_answer == False, 1), else_=0)).label('no_responses')
        ).where(
            and_(
                SessionResponse.session_id == Session.id,
                Session.user_id.in_(team_member_ids)
            )
        )
    )
    responses_data = responses_result.first()
    total_responses = responses_data.total_responses or 0
    total_no_responses = responses_data.no_responses or 0

    # Get top 3 missing items
    top_missing_result = await db.execute(
        select(
            ChecklistItem.id,
            ChecklistItem.title.label('item_text'),
            ChecklistCategory.name.label('category_name'),
            func.count(SessionResponse.id).label('missing_count')
        ).join(
            ChecklistCategory, ChecklistItem.category_id == ChecklistCategory.id
        ).where(
            and_(
                SessionResponse.session_id == Session.id,
                Session.user_id.in_(team_member_ids),
                SessionResponse.item_id == ChecklistItem.id,
                SessionResponse.ai_answer == False
            )
        ).group_by(ChecklistItem.id, ChecklistItem.title, ChecklistCategory.name)
        .order_by(desc(func.count(SessionResponse.id)))
        .limit(3)
    )

    top_missing_items = []
    for item_id, item_text, category_name, missing_count in top_missing_result:
        missing_percentage = (missing_count / total_sessions * 100) if total_sessions > 0 else 0
        top_missing_items.append(MissingItemAnalysis(
            item_id=item_id,
            item_text=item_text,
            category_name=category_name,
            missing_count=missing_count,
            total_sessions=total_sessions,
            missing_percentage=round(missing_percentage, 1)
        ))

    no_percentage = (total_no_responses / total_responses * 100) if total_responses > 0 else 0

    return TeamNoSummary(
        total_sessions=total_sessions,
        total_responses=total_responses,
        total_no_responses=total_no_responses,
        no_percentage=round(no_percentage, 1),
        top_missing_items=top_missing_items
    )


@router.get("/overview", response_model=ManagerDashboardOverview)
async def get_dashboard_overview(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    sort_by: str = Query("updated_at", regex="^(updated_at|created_at|score|salesperson)$"),
    order: str = Query("desc", regex="^(asc|desc)$")
):
    """
    Get complete manager dashboard overview in a single request

    Returns all dashboard data:
    - Stats (active checklists, team members, average score, alerts)
    - Notifications (stalled, at-risk, high-score lost deals)
    - Active checklists (with sorting support)
    - Team training gaps (top missing items)

    **Query Parameters:**
    - sort_by: Field to sort active checklists by (updated_at, created_at, score, salesperson)
    - order: Sort order (asc, desc)

    **Permissions:**
    - MANAGER: Team overview
    - ADMIN: Organization overview
    - SYSTEM_ADMIN: All overview
    """
    if not can_view_team_data(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only managers and admins can access dashboard overview"
        )

    team_member_ids = await get_team_members(current_user, db)

    # 1. Get Stats
    # Count active checklists
    active_result = await db.execute(
        select(func.count(Session.id)).where(
            and_(
                Session.user_id.in_(team_member_ids),
                Session.status.in_([
                    SessionStatus.PENDING_REVIEW,
                    SessionStatus.COMPLETED
                ])
            )
        )
    )
    total_active = active_result.scalar() or 0

    # Average team score
    score_result = await db.execute(
        select(func.avg(ScoringResult.total_score)).where(
            and_(
                ScoringResult.session_id == Session.id,
                Session.user_id.in_(team_member_ids)
            )
        )
    )
    avg_score = score_result.scalar()

    # Count alerts (will be recalculated in notifications, but needed for stats)
    stalled_count = await db.execute(
        select(func.count(Session.id)).where(
            and_(
                Session.user_id.in_(team_member_ids),
                Session.updated_at < datetime.utcnow() - timedelta(days=30),
                Session.status != SessionStatus.COMPLETED
            )
        )
    )

    at_risk_count = await db.execute(
        select(func.count(Session.id)).where(
            and_(
                Session.user_id.in_(team_member_ids),
                Session.id == ScoringResult.session_id,
                ScoringResult.total_score <= 30
            )
        )
    )

    total_alerts = (stalled_count.scalar() or 0) + (at_risk_count.scalar() or 0)

    stats = DashboardStats(
        total_active_checklists=total_active,
        total_team_members=len(team_member_ids),
        average_team_score=round(avg_score / 5) * 5 if avg_score else None,
        total_alerts=total_alerts
    )

    # 2. Get Notifications
    # Stalled deals (30+ days inactive)
    stalled_result = await db.execute(
        select(Session, User, ScoringResult).where(
            and_(
                Session.user_id.in_(team_member_ids),
                Session.updated_at < datetime.utcnow() - timedelta(days=30),
                Session.status != SessionStatus.COMPLETED,
                Session.user_id == User.id
            )
        ).outerjoin(ScoringResult, Session.id == ScoringResult.session_id)
        .order_by(Session.updated_at.asc())
        .limit(50)
    )

    stalled_deals = []
    for session, user, scoring in stalled_result:
        days_inactive = (datetime.utcnow() - session.updated_at).days
        stalled_deals.append(DealAlert(
            session_id=session.id,
            customer_name=session.customer_name,
            salesperson_name=f"{user.first_name or ''} {user.last_name or ''}".strip() or user.email,
            salesperson_id=user.id,
            alert_type="stalled",
            score=scoring.total_score if scoring else None,
            days_inactive=days_inactive,
            deal_stage=session.deal_stage,
            last_updated=session.updated_at
        ))

    # At-risk deals (scores 0-30)
    at_risk_result = await db.execute(
        select(Session, User, ScoringResult).where(
            and_(
                Session.user_id.in_(team_member_ids),
                Session.id == ScoringResult.session_id,
                ScoringResult.total_score <= 30,
                Session.user_id == User.id
            )
        ).order_by(ScoringResult.total_score.asc())
        .limit(50)
    )

    at_risk_deals = []
    for session, user, scoring in at_risk_result:
        at_risk_deals.append(DealAlert(
            session_id=session.id,
            customer_name=session.customer_name,
            salesperson_name=f"{user.first_name or ''} {user.last_name or ''}".strip() or user.email,
            salesperson_id=user.id,
            alert_type="at_risk",
            score=scoring.total_score,
            deal_stage=session.deal_stage,
            last_updated=session.updated_at
        ))

    # High-scoring lost deals (70+ but lost/no decision/disengaged)
    try:
        high_score_lost_result = await db.execute(
            select(Session, User, ScoringResult).where(
                and_(
                    Session.user_id.in_(team_member_ids),
                    Session.id == ScoringResult.session_id,
                    ScoringResult.total_score >= 70,
                    Session.deal_stage.in_([DealStage.LOST, DealStage.NO_DECISION, DealStage.DISENGAGED]),
                    Session.user_id == User.id
                )
            ).order_by(desc(ScoringResult.total_score))
            .limit(50)
        )
    except Exception as e:
        # If DISENGAGED is not in the database enum yet, rollback and query without it
        if "DISENGAGED" in str(e) or "disengaged" in str(e) or "InFailedSQLTransactionError" in str(e):
            logger.warning("DISENGAGED enum value not found in database, querying without it. Run migration 0090406d8bf9.")
            await db.rollback()
            high_score_lost_result = await db.execute(
                select(Session, User, ScoringResult).where(
                    and_(
                        Session.user_id.in_(team_member_ids),
                        Session.id == ScoringResult.session_id,
                        ScoringResult.total_score >= 70,
                        Session.deal_stage.in_([DealStage.LOST, DealStage.NO_DECISION]),
                        Session.user_id == User.id
                    )
                ).order_by(desc(ScoringResult.total_score))
                .limit(50)
            )
        else:
            raise

    high_score_lost_deals = []
    for session, user, scoring in high_score_lost_result:
        high_score_lost_deals.append(DealAlert(
            session_id=session.id,
            customer_name=session.customer_name,
            salesperson_name=f"{user.first_name or ''} {user.last_name or ''}".strip() or user.email,
            salesperson_id=user.id,
            alert_type="high_score_lost",
            score=scoring.total_score,
            deal_stage=session.deal_stage,
            last_updated=session.updated_at
        ))

    notifications = DashboardNotifications(
        stalled_deals=stalled_deals,
        at_risk_deals=at_risk_deals,
        high_score_lost_deals=high_score_lost_deals,
        total_alerts=len(stalled_deals) + len(at_risk_deals) + len(high_score_lost_deals)
    )

    # 3. Get Active Checklists (with sorting)
    query = (
        select(Session, User, ScoringResult)
        .where(
            and_(
                Session.user_id.in_(team_member_ids),
                Session.status.in_([
                    SessionStatus.PENDING_REVIEW,
                    SessionStatus.COMPLETED
                ]),
                Session.user_id == User.id
            )
        )
        .outerjoin(ScoringResult, Session.id == ScoringResult.session_id)
    )

    # Apply sorting
    if sort_by == "updated_at":
        query = query.order_by(desc(Session.updated_at) if order == "desc" else Session.updated_at)
    elif sort_by == "created_at":
        query = query.order_by(desc(Session.created_at) if order == "desc" else Session.created_at)
    elif sort_by == "score":
        query = query.order_by(desc(ScoringResult.total_score) if order == "desc" else ScoringResult.total_score)
    elif sort_by == "salesperson":
        query = query.order_by(desc(User.email) if order == "desc" else User.email)

    result = await db.execute(query)

    active_checklists = []
    for session, user, scoring in result:
        active_checklists.append(ActiveChecklist(
            session_id=session.id,
            customer_name=session.customer_name,
            opportunity_name=session.opportunity_name,
            salesperson_name=f"{user.first_name or ''} {user.last_name or ''}".strip() or user.email,
            salesperson_id=user.id,
            score=scoring.total_score if scoring else None,
            status=session.status.value,
            deal_stage=session.deal_stage,
            created_at=session.created_at,
            updated_at=session.updated_at
        ))

    # 4. Get Team Training Gaps (top missing items)
    total_sessions_result = await db.execute(
        select(func.count(Session.id)).where(Session.user_id.in_(team_member_ids))
    )
    total_sessions = total_sessions_result.scalar() or 0

    # Get top 3 missing items
    top_missing_result = await db.execute(
        select(
            ChecklistItem.id,
            ChecklistItem.title.label('item_text'),
            ChecklistCategory.name.label('category_name'),
            func.count(SessionResponse.id).label('missing_count')
        ).join(
            ChecklistCategory, ChecklistItem.category_id == ChecklistCategory.id
        ).where(
            and_(
                SessionResponse.session_id == Session.id,
                Session.user_id.in_(team_member_ids),
                SessionResponse.item_id == ChecklistItem.id,
                SessionResponse.ai_answer == False
            )
        ).group_by(ChecklistItem.id, ChecklistItem.title, ChecklistCategory.name)
        .order_by(desc(func.count(SessionResponse.id)))
        .limit(3)
    )

    top_missing_items = []
    for item_id, item_text, category_name, missing_count in top_missing_result:
        missing_percentage = (missing_count / total_sessions * 100) if total_sessions > 0 else 0
        top_missing_items.append(MissingItemAnalysis(
            item_id=item_id,
            item_text=item_text,
            category_name=category_name,
            missing_count=missing_count,
            total_sessions=total_sessions,
            missing_percentage=round(missing_percentage, 1)
        ))

    team_training_gaps = TeamTrainingGaps(
        top_missing_items=top_missing_items
    )

    return ManagerDashboardOverview(
        stats=stats,
        notifications=notifications,
        active_checklists=active_checklists,
        team_training_gaps=team_training_gaps
    )
