"""
Scoring API endpoints
Calculate scores and risk bands for sessions
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import Dict, List

from app.db.session import get_db
from app.models.session import Session, SessionResponse
from app.models.checklist import ChecklistItem, ChecklistCategory
from app.models.scoring import ScoringResult
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
        item_score = 0
        if response.is_validated is True:
            item_score = 10
            total_score += 10
            validated_items.append({
                "id": item.id,
                "title": item.title,
                "category": category.name,
                "score": 10
            })
        elif response.is_validated is False:
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
            "validated": response.is_validated
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

    # Delete existing scoring result
    await db.execute(
        select(ScoringResult).where(ScoringResult.session_id == session_id)
    )

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