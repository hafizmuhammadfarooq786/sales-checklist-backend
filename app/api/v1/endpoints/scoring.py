"""
Scoring API endpoints
Calculate scores and risk bands for sessions
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import Dict, List
from datetime import datetime

from app.db.session import get_db
from app.models.session import Session, SessionResponse, SessionStatus
from app.models.checklist import ChecklistItem, ChecklistCategory
from app.models.scoring import ScoringResult, ScoreHistory
from app.api.dependencies import get_current_user_id

router = APIRouter()


@router.post("/{session_id}/calculate", status_code=status.HTTP_201_CREATED)
async def calculate_session_score(
    session_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Calculate score for a session based on checklist responses
    Scoring logic: 10 points per validated item (Yes), 0 for No, total out of 100
    """
    # Verify session belongs to user
    session_result = await db.execute(
        select(Session).where(
            Session.id == session_id,
            Session.user_id == user_id,
        )
    )
    session = session_result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    # Get all responses with checklist items and categories
    responses_result = await db.execute(
        select(SessionResponse)
        .where(SessionResponse.session_id == session_id)
        .options(
            selectinload(SessionResponse.item).selectinload(ChecklistItem.category)
        )
        .order_by(SessionResponse.item_id)
    )
    responses = responses_result.scalars().all()

    if not responses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No responses found for this session. Initialize responses first."
        )

    # Calculate score (equal weight: 10 points per Yes, 0 per No)
    total_score = 0
    max_possible_score = len(responses) * 10  # 10 points per item
    category_scores = {}
    validated_items = []
    unvalidated_items = []
    
    for response in responses:
        item = response.item
        category = item.category
        
        # Track category
        if category.id not in category_scores:
            category_scores[category.id] = {
                "name": category.name,
                "score": 0,
                "max_score": 0,
                "items": []
            }
        
        category_scores[category.id]["max_score"] += 10

        # Calculate score for this item
        # Use user_answer if provided, otherwise use ai_answer
        final_answer = response.user_answer if response.user_answer is not None else response.ai_answer

        item_score = 0
        if final_answer is True:
            item_score = 10
            total_score += 10
            validated_items.append({
                "id": item.id,
                "title": item.title,
                "category": category.name,
                "score": 10
            })
        elif final_answer is False:
            unvalidated_items.append({
                "id": item.id,
                "title": item.title,
                "category": category.name,
                "score": 0
            })
        # None/null means not answered yet, gets 0 points

        category_scores[category.id]["score"] += item_score
        category_scores[category.id]["items"].append({
            "title": item.title,
            "score": item_score,
            "validated": final_answer
        })

    # Calculate percentage
    percentage_score = (total_score / max_possible_score * 100) if max_possible_score > 0 else 0

    # Determine risk band
    if percentage_score >= 80:
        risk_band = "green"
        risk_label = "Healthy"
    elif percentage_score >= 60:
        risk_band = "yellow" 
        risk_label = "Caution"
    else:
        risk_band = "red"
        risk_label = "At Risk"

    # Get top 3 strengths (highest scoring items)
    strengths = sorted(validated_items, key=lambda x: x["score"], reverse=True)[:3]
    
    # Get bottom 3 gaps (lowest scoring items)
    gaps = sorted(unvalidated_items, key=lambda x: x["score"])[:3]

    # Get previous scoring result to calculate score change
    previous_result_query = await db.execute(
        select(ScoringResult).where(ScoringResult.session_id == session_id)
    )
    previous_result = previous_result_query.scalar_one_or_none()

    # Calculate score change
    score_change = None
    if previous_result:
        score_change = percentage_score - previous_result.total_score

    # Delete existing scoring result (we'll create a new one)
    if previous_result:
        db.delete(previous_result)
        await db.flush()  # Flush to ensure delete happens before insert

    # Create new scoring result
    scoring_result = ScoringResult(
        session_id=session_id,
        total_score=percentage_score,
        risk_band=risk_band,
        category_scores=category_scores,
        top_strengths=[s['title'] for s in strengths[:3]],
        top_gaps=[g['title'] for g in gaps[:3]],
        items_validated=len(validated_items),
        items_total=len(responses)
    )

    db.add(scoring_result)
    await db.flush()  # Flush to get scoring_result.id before creating history
    await db.refresh(scoring_result)

    # Create score history record
    score_history_entry = ScoreHistory(
        session_id=session_id,
        scoring_result_id=scoring_result.id,
        total_score=percentage_score,
        risk_band=risk_band,
        items_validated=len(validated_items),
        items_total=len(responses),
        calculated_at=datetime.utcnow(),
        score_change=score_change,
        trigger_event="manual_calculation" if previous_result else "initial_calculation",
        created_by_user_id=user_id
    )

    db.add(score_history_entry)
    await db.commit()
    await db.refresh(scoring_result)

    # Update session status to scoring
    session.status = SessionStatus.SCORING
    await db.commit()

    return {
        "session_id": session_id,
        "total_score": int(percentage_score),
        "max_possible_score": 100,
        "percentage": round(percentage_score, 1),
        "risk_band": risk_band,
        "risk_label": risk_label,
        "category_breakdown": list(category_scores.values()),
        "strengths": strengths,
        "gaps": gaps,
        "summary": {
            "validated_items": len(validated_items),
            "unvalidated_items": len(unvalidated_items),
            "total_items": len(responses)
        },
        "scoring_result_id": scoring_result.id
    }


@router.get("/{session_id}/score")
async def get_session_score(
    session_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Get existing score for a session
    """
    # Verify session belongs to user
    session_result = await db.execute(
        select(Session).where(
            Session.id == session_id,
            Session.user_id == user_id,
        )
    )
    session = session_result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
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
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Get complete score history for a session.
    Returns all score calculations ordered by most recent first.
    Includes score changes, trigger events, and timestamps.
    """
    # Verify session belongs to user
    session_result = await db.execute(
        select(Session).where(
            Session.id == session_id,
            Session.user_id == user_id,
        )
    )
    session = session_result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
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