"""
Coaching Report aggregations.

Builds the leader / team / individual payload from existing sessions,
responses, scores, manager notes, and score history.
"""
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.checklist import ChecklistItem
from app.models.manager_note import ManagerNote
from app.models.scoring import ScoreHistory, ScoringResult
from app.models.session import DealStage, Session, SessionResponse, SessionStatus
from app.models.user import User
from app.services.coaching_service import HARDCODED_COACHING_FEEDBACK
from app.services.risk_band_service import AT_RISK_MAX_SCORE, EXCELLENT_MIN_SCORE

REVIEWABLE_STATUSES = [
    SessionStatus.PENDING_REVIEW,
    SessionStatus.COMPLETED,
]

CLOSED_STAGES = {
    DealStage.WON,
    DealStage.LOST,
    DealStage.NO_DECISION,
    DealStage.DISENGAGED,
}

LOST_REVIEW_STAGES = {
    DealStage.LOST,
    DealStage.NO_DECISION,
    DealStage.DISENGAGED,
}


def display_name(user: User) -> str:
    full = f"{user.first_name or ''} {user.last_name or ''}".strip()
    return full or user.email


def stage_value(stage: Any) -> Optional[str]:
    if stage is None:
        return None
    if isinstance(stage, DealStage):
        return stage.value
    return str(stage).strip().lower() or None


def is_open_deal(stage: Any) -> bool:
    if stage is None:
        return True
    if isinstance(stage, DealStage):
        return stage not in CLOSED_STAGES
    return stage_value(stage) not in {s.value for s in CLOSED_STAGES}


def is_won(stage: Any) -> bool:
    return stage == DealStage.WON or stage_value(stage) == DealStage.WON.value


def is_lost_review(stage: Any) -> bool:
    if isinstance(stage, DealStage):
        return stage in LOST_REVIEW_STAGES
    return stage_value(stage) in {s.value for s in LOST_REVIEW_STAGES}


def final_answer(response: SessionResponse) -> Optional[bool]:
    if response.user_answer is not None:
        return response.user_answer
    return response.ai_answer


def evidence_status(answer: Optional[bool]) -> str:
    if answer is True:
        return "yes"
    if answer is False:
        return "gap"
    return "blank"


def coaching_text_for(title: str) -> str:
    if title in HARDCODED_COACHING_FEEDBACK:
        return HARDCODED_COACHING_FEEDBACK[title]
    lowered = title.lower()
    for key, value in HARDCODED_COACHING_FEEDBACK.items():
        if key.lower() in lowered or lowered in key.lower():
            return value
    return f"Coach the missing customer evidence for {title}."


def snapshot_answer_map(snapshot: Any) -> Dict[int, bool]:
    answers: Dict[int, bool] = {}
    if not isinstance(snapshot, list):
        return answers
    for row in snapshot:
        if not isinstance(row, dict):
            continue
        item_id = row.get("item_id")
        answer = row.get("answer")
        if item_id is None or answer is None:
            continue
        answers[int(item_id)] = bool(answer)
    return answers


def empty_overview(checklist_items: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "kpis": {
            "active_checklists": 0,
            "coaching_opportunities": 0,
            "blank_answers": 0,
            "lost_deals_to_review": 0,
            "gaps_closed": 0,
            "won_count": 0,
            "lost_count": 0,
        },
        "checklist_items": checklist_items,
        "grid_rows": [],
        "common_gaps": [],
        "salesperson_priorities": [],
        "priority_opportunities": [],
        "lost_deals": [],
        "won_deals": [],
        "salespeople": [],
        "gaps_closed_events": [],
        "weekly_trend": [],
        "win_patterns": [],
        "lose_patterns": [],
        "next_behavior_to_coach": None,
    }


async def _load_checklist_items(db: AsyncSession) -> List[ChecklistItem]:
    result = await db.execute(
        select(ChecklistItem)
        .where(ChecklistItem.is_active.is_(True))
        .order_by(ChecklistItem.order.asc())
    )
    return list(result.scalars().all())


async def build_coaching_report_overview(
    *,
    db: AsyncSession,
    team_member_ids: List[int],
    range_start: datetime,
    range_end: datetime,
) -> Dict[str, Any]:
    items = await _load_checklist_items(db)
    checklist_items = [
        {
            "id": item.id,
            "order": item.order,
            "title": item.title,
            "coaching_text": coaching_text_for(item.title),
        }
        for item in items
    ]
    item_by_id = {item.id: item for item in items}

    if not team_member_ids:
        return empty_overview(checklist_items)

    session_filter = and_(
        Session.user_id.in_(team_member_ids),
        Session.status.in_(REVIEWABLE_STATUSES),
        Session.created_at >= range_start,
        Session.created_at <= range_end,
        Session.updated_at <= range_end,
    )

    sessions_result = await db.execute(
        select(Session)
        .options(
            selectinload(Session.user),
            selectinload(Session.responses),
            selectinload(Session.scoring_result),
        )
        .where(session_filter)
        .order_by(Session.updated_at.desc())
    )
    sessions: List[Session] = list(sessions_result.scalars().unique().all())
    session_ids = [session.id for session in sessions]

    latest_notes: Dict[int, ManagerNote] = {}
    note_counts: Dict[int, int] = {}
    score_histories: Dict[int, List[ScoreHistory]] = defaultdict(list)

    if session_ids:
        latest_subq = (
            select(
                ManagerNote.session_id,
                func.max(ManagerNote.id).label("max_id"),
            )
            .where(
                ManagerNote.session_id.in_(session_ids),
                ManagerNote.note_text.isnot(None),
            )
            .group_by(ManagerNote.session_id)
            .subquery()
        )
        notes_result = await db.execute(
            select(ManagerNote).join(
                latest_subq, ManagerNote.id == latest_subq.c.max_id
            )
        )
        for note in notes_result.scalars().all():
            if not (note.note_text or "").strip():
                continue
            latest_notes[note.session_id] = note

        count_result = await db.execute(
            select(ManagerNote.session_id, func.count(ManagerNote.id))
            .where(ManagerNote.session_id.in_(session_ids))
            .group_by(ManagerNote.session_id)
        )
        note_counts = {row[0]: int(row[1]) for row in count_result.all()}

        history_result = await db.execute(
            select(ScoreHistory)
            .where(ScoreHistory.session_id.in_(session_ids))
            .order_by(ScoreHistory.session_id.asc(), ScoreHistory.version_number.asc())
        )
        for history in history_result.scalars().all():
            score_histories[history.session_id].append(history)

    trend_start = range_end - timedelta(weeks=12)
    trend_session_filter = and_(
        Session.user_id.in_(team_member_ids),
        Session.status.in_(REVIEWABLE_STATUSES),
        Session.created_at >= trend_start,
        Session.created_at <= range_end,
    )
    trend_sessions_result = await db.execute(
        select(Session, ScoringResult)
        .outerjoin(ScoringResult, ScoringResult.session_id == Session.id)
        .where(trend_session_filter)
    )
    trend_rows = list(trend_sessions_result.all())

    recent_history_result = await db.execute(
        select(ScoreHistory.session_id)
        .join(Session, ScoreHistory.session_id == Session.id)
        .where(
            Session.user_id.in_(team_member_ids),
            ScoreHistory.calculated_at >= trend_start,
            ScoreHistory.calculated_at <= range_end,
        )
        .distinct()
    )
    trend_history_session_ids = [row[0] for row in recent_history_result.all()]
    trend_histories: List[ScoreHistory] = []
    if trend_history_session_ids:
        full_history_result = await db.execute(
            select(ScoreHistory)
            .where(ScoreHistory.session_id.in_(trend_history_session_ids))
            .order_by(ScoreHistory.session_id.asc(), ScoreHistory.version_number.asc())
        )
        trend_histories = list(full_history_result.scalars().all())

    grid_rows: List[Dict[str, Any]] = []
    lost_deals: List[Dict[str, Any]] = []
    won_deals: List[Dict[str, Any]] = []
    gap_counts_by_item: Dict[int, int] = defaultdict(int)
    active_sessions_with_item: Dict[int, int] = defaultdict(int)
    yes_by_item_won: Dict[int, int] = defaultdict(int)
    gap_by_item_lost: Dict[int, int] = defaultdict(int)
    won_session_count = 0
    lost_session_count = 0
    salesperson_stats: Dict[int, Dict[str, Any]] = {}
    salespeople_map: Dict[int, str] = {}

    for session in sessions:
        user = session.user
        salesperson_name = display_name(user)
        salespeople_map[user.id] = salesperson_name
        responses_by_item = {response.item_id: response for response in session.responses}

        cells: List[Dict[str, Any]] = []
        yes_count = 0
        gap_count = 0
        blank_count = 0
        first_gap_item: Optional[ChecklistItem] = None

        for item in items:
            response = responses_by_item.get(item.id)
            answer = final_answer(response) if response is not None else None
            status = evidence_status(answer)
            cells.append(
                {
                    "item_id": item.id,
                    "order": item.order,
                    "status": status,
                }
            )
            if status == "yes":
                yes_count += 1
            elif status == "gap":
                gap_count += 1
                if first_gap_item is None:
                    first_gap_item = item
            else:
                blank_count += 1

        note = latest_notes.get(session.id)
        scoring: Optional[ScoringResult] = session.scoring_result
        score = scoring.total_score if scoring is not None else None
        days_active = max(0, (range_end.date() - session.created_at.date()).days)

        if is_open_deal(session.deal_stage):
            grid_rows.append(
                {
                    "session_id": session.id,
                    "salesperson_id": user.id,
                    "salesperson_name": salesperson_name,
                    "customer_name": session.customer_name,
                    "opportunity_name": session.opportunity_name,
                    "days_active": days_active,
                    "deal_stage": stage_value(session.deal_stage),
                    "score": score,
                    "items": cells,
                    "yes_count": yes_count,
                    "gap_count": gap_count,
                    "blank_count": blank_count,
                    "coaching_note_id": note.id if note else None,
                    "coaching_note_text": note.note_text if note else None,
                    "coaching_note_count": note_counts.get(session.id, 0),
                    "critical_gap_item_id": first_gap_item.id if first_gap_item else None,
                    "critical_gap_title": first_gap_item.title if first_gap_item else None,
                    "recommended_action": (
                        coaching_text_for(first_gap_item.title) if first_gap_item else None
                    ),
                }
            )

            for cell in cells:
                item_id = cell["item_id"]
                active_sessions_with_item[item_id] += 1
                if cell["status"] == "gap":
                    gap_counts_by_item[item_id] += 1

            stats = salesperson_stats.setdefault(
                user.id,
                {
                    "salesperson_id": user.id,
                    "salesperson_name": salesperson_name,
                    "session_count": 0,
                    "yes_count": 0,
                    "gap_count": 0,
                    "blank_count": 0,
                    "item_gaps": defaultdict(int),
                },
            )
            stats["session_count"] += 1
            stats["yes_count"] += yes_count
            stats["gap_count"] += gap_count
            stats["blank_count"] += blank_count
            for cell in cells:
                if cell["status"] == "gap":
                    stats["item_gaps"][cell["item_id"]] += 1

        closed_payload = {
            "session_id": session.id,
            "salesperson_id": user.id,
            "salesperson_name": salesperson_name,
            "customer_name": session.customer_name,
            "opportunity_name": session.opportunity_name,
            "missing_count": gap_count,
            "present_count": yes_count,
            "score": score,
            "deal_stage": stage_value(session.deal_stage),
        }
        if is_won(session.deal_stage):
            won_deals.append(closed_payload)
            won_session_count += 1
            for cell in cells:
                if cell["status"] == "yes":
                    yes_by_item_won[cell["item_id"]] += 1
        elif is_lost_review(session.deal_stage):
            lost_deals.append(closed_payload)
            lost_session_count += 1
            for cell in cells:
                if cell["status"] == "gap":
                    gap_by_item_lost[cell["item_id"]] += 1

    gaps_closed_events: List[Dict[str, Any]] = []
    for session in sessions:
        histories = score_histories.get(session.id, [])
        if len(histories) < 2:
            continue
        for previous, current in zip(histories, histories[1:]):
            if current.calculated_at < range_start or current.calculated_at > range_end:
                continue
            prev_answers = snapshot_answer_map(previous.responses_snapshot)
            next_answers = snapshot_answer_map(current.responses_snapshot)
            for item_id, was_yes in prev_answers.items():
                now_yes = next_answers.get(item_id)
                if was_yes is False and now_yes is True:
                    item = item_by_id.get(item_id)
                    if item is None:
                        continue
                    note = latest_notes.get(session.id)
                    gaps_closed_events.append(
                        {
                            "session_id": session.id,
                            "salesperson_id": session.user_id,
                            "salesperson_name": display_name(session.user),
                            "customer_name": session.customer_name,
                            "opportunity_name": session.opportunity_name,
                            "item_id": item.id,
                            "item_order": item.order,
                            "item_title": item.title,
                            "sales_behavior_performed": coaching_text_for(item.title),
                            "coaching_provided": note.note_text if note else None,
                            "closed_at": current.calculated_at,
                        }
                    )

    common_gaps = []
    active_row_count = len(grid_rows) or 1
    for item in items:
        missing = gap_counts_by_item.get(item.id, 0)
        if missing == 0:
            continue
        denom = active_sessions_with_item.get(item.id, active_row_count)
        common_gaps.append(
            {
                "item_id": item.id,
                "item_order": item.order,
                "title": item.title,
                "missing_count": missing,
                "total_sessions": denom,
                "gap_percentage": round((missing / denom) * 100, 1) if denom else 0.0,
                "coaching_text": coaching_text_for(item.title),
            }
        )
    common_gaps.sort(key=lambda row: (-row["gap_percentage"], row["item_order"]))

    next_behavior = None
    if common_gaps:
        top = common_gaps[0]
        next_behavior = {
            "item_id": top["item_id"],
            "item_order": top["item_order"],
            "title": top["title"],
            "coaching_text": top["coaching_text"],
        }

    salesperson_priorities = []
    for stats in salesperson_stats.values():
        answered = stats["yes_count"] + stats["gap_count"]
        proficiency = round((stats["yes_count"] / answered) * 100, 1) if answered else 0.0
        lowest_item_id = None
        lowest_title = None
        lowest_count = 0
        if stats["item_gaps"]:
            lowest_item_id = max(stats["item_gaps"].items(), key=lambda pair: pair[1])[0]
            lowest_count = stats["item_gaps"][lowest_item_id]
            lowest_item = item_by_id.get(lowest_item_id)
            lowest_title = lowest_item.title if lowest_item else None
        salesperson_priorities.append(
            {
                "salesperson_id": stats["salesperson_id"],
                "salesperson_name": stats["salesperson_name"],
                "session_count": stats["session_count"],
                "proficiency": proficiency,
                "gap_count": stats["gap_count"],
                "yes_count": stats["yes_count"],
                "blank_count": stats["blank_count"],
                "lowest_gap_item_id": lowest_item_id,
                "lowest_gap_title": lowest_title,
                "lowest_gap_count": lowest_count,
                "coaching_text": coaching_text_for(lowest_title) if lowest_title else None,
            }
        )
    salesperson_priorities.sort(key=lambda row: (row["proficiency"], -row["gap_count"]))

    def opportunity_priority(row: Dict[str, Any]) -> Tuple[int, float, int]:
        score = row["score"] if row["score"] is not None else 0
        return (0 if score <= AT_RISK_MAX_SCORE else 1, score, -row["gap_count"])

    priority_opportunities = []
    for row in sorted(grid_rows, key=opportunity_priority)[:8]:
        score = row["score"] if row["score"] is not None else 0
        if score <= AT_RISK_MAX_SCORE or row["gap_count"] >= 7:
            label = "critical"
        elif score < EXCELLENT_MIN_SCORE or row["gap_count"] >= 4:
            label = "high"
        else:
            label = "watch"
        priority_opportunities.append(
            {
                "session_id": row["session_id"],
                "salesperson_id": row["salesperson_id"],
                "salesperson_name": row["salesperson_name"],
                "customer_name": row["customer_name"],
                "opportunity_name": row["opportunity_name"],
                "score": row["score"],
                "gap_count": row["gap_count"],
                "priority": label,
                "critical_gap_title": row["critical_gap_title"],
                "recommended_action": row["recommended_action"],
            }
        )

    win_patterns = []
    lose_patterns = []
    for item in items:
        if won_session_count:
            present = yes_by_item_won.get(item.id, 0)
            win_patterns.append(
                {
                    "item_id": item.id,
                    "item_order": item.order,
                    "title": item.title,
                    "percentage": round((present / won_session_count) * 100, 1),
                }
            )
        if lost_session_count:
            missing = gap_by_item_lost.get(item.id, 0)
            lose_patterns.append(
                {
                    "item_id": item.id,
                    "item_order": item.order,
                    "title": item.title,
                    "percentage": round((missing / lost_session_count) * 100, 1),
                }
            )
    win_patterns.sort(key=lambda row: (-row["percentage"], row["item_order"]))
    lose_patterns.sort(key=lambda row: (-row["percentage"], row["item_order"]))

    weekly_trend = _build_weekly_trend(
        range_end=range_end,
        trend_rows=trend_rows,
        trend_histories=trend_histories,
        item_ids={item.id for item in items},
    )

    coaching_opportunities = sum(row["gap_count"] for row in grid_rows)
    blank_answers = sum(row["blank_count"] for row in grid_rows)

    salespeople = [
        {"id": user_id, "name": name}
        for user_id, name in sorted(salespeople_map.items(), key=lambda pair: pair[1].lower())
    ]

    lost_deals.sort(key=lambda row: -row["missing_count"])
    won_deals.sort(key=lambda row: -row["present_count"])
    gaps_closed_events.sort(key=lambda row: row["closed_at"], reverse=True)

    return {
        "kpis": {
            "active_checklists": len(grid_rows),
            "coaching_opportunities": coaching_opportunities,
            "blank_answers": blank_answers,
            "lost_deals_to_review": len(lost_deals),
            "gaps_closed": len(gaps_closed_events),
            "won_count": len(won_deals),
            "lost_count": sum(
                1 for deal in lost_deals if deal["deal_stage"] == DealStage.LOST.value
            ),
        },
        "checklist_items": checklist_items,
        "grid_rows": grid_rows,
        "common_gaps": common_gaps[:6],
        "salesperson_priorities": salesperson_priorities,
        "priority_opportunities": priority_opportunities,
        "lost_deals": lost_deals,
        "won_deals": won_deals,
        "salespeople": salespeople,
        "gaps_closed_events": gaps_closed_events[:20],
        "weekly_trend": weekly_trend,
        "win_patterns": win_patterns[:6],
        "lose_patterns": lose_patterns[:6],
        "next_behavior_to_coach": next_behavior,
    }


def _build_weekly_trend(
    *,
    range_end: datetime,
    trend_rows: List[Tuple[Session, Optional[ScoringResult]]],
    trend_histories: List[ScoreHistory],
    item_ids: set,
) -> List[Dict[str, Any]]:
    weeks: List[Dict[str, Any]] = []
    end_date = range_end.date()
    for index in range(11, -1, -1):
        week_end_date = end_date - timedelta(weeks=index)
        week_start_date = week_end_date - timedelta(days=6)
        week_start = datetime.combine(week_start_date, datetime.min.time())
        week_end = datetime.combine(week_end_date, datetime.max.time())
        weeks.append(
            {
                "week_start": week_start,
                "week_end": week_end,
                "label": week_start.strftime("%b %d"),
                "scores": [],
                "gaps_closed": 0,
            }
        )

    def week_index(moment: datetime) -> Optional[int]:
        for i, week in enumerate(weeks):
            if week["week_start"] <= moment <= week["week_end"]:
                return i
        return None

    for session, scoring in trend_rows:
        idx = week_index(session.created_at)
        if idx is None or scoring is None:
            continue
        weeks[idx]["scores"].append(scoring.total_score)

    histories_by_session: Dict[int, List[ScoreHistory]] = defaultdict(list)
    for history in trend_histories:
        histories_by_session[history.session_id].append(history)

    for session_histories in histories_by_session.values():
        ordered = sorted(session_histories, key=lambda row: row.version_number)
        for previous, current in zip(ordered, ordered[1:]):
            idx = week_index(current.calculated_at)
            if idx is None:
                continue
            prev_answers = snapshot_answer_map(previous.responses_snapshot)
            next_answers = snapshot_answer_map(current.responses_snapshot)
            closed = 0
            for item_id in item_ids:
                if prev_answers.get(item_id) is False and next_answers.get(item_id) is True:
                    closed += 1
            weeks[idx]["gaps_closed"] += closed

    trend = []
    for week in weeks:
        scores = week["scores"]
        trend.append(
            {
                "week_start": week["week_start"].date().isoformat(),
                "label": week["label"],
                "average_score": round(sum(scores) / len(scores), 1) if scores else None,
                "gaps_closed": week["gaps_closed"],
                "session_count": len(scores),
            }
        )
    return trend
