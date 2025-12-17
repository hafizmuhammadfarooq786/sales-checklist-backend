"""
Checklist™ API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List

from app.db.session import get_db
from app.models import ChecklistCategory, ChecklistItem
from app.models.checklist_behaviour import ChecklistItemBehaviour
from app.schemas.checklist import (
    ChecklistCategoryResponse,
    ChecklistCategoryWithItems,
    ChecklistItemResponse,
    ChecklistSummary,
)

router = APIRouter()


@router.get("/summary", response_model=ChecklistSummary)
async def get_checklist_summary(
    db: AsyncSession = Depends(get_db)
):
    """
    Get summary of all checklist categories.
    Returns total counts and list of categories.
    """
    # Get all active categories
    result = await db.execute(
        select(ChecklistCategory)
        .where(ChecklistCategory.is_active == True)
        .order_by(ChecklistCategory.order)
    )
    categories = result.scalars().all()

    # Count total items
    items_result = await db.execute(
        select(ChecklistItem)
        .where(ChecklistItem.is_active == True)
    )
    total_items = len(items_result.scalars().all())

    return ChecklistSummary(
        total_categories=len(categories),
        total_items=total_items,
        categories=[ChecklistCategoryResponse.model_validate(cat) for cat in categories]
    )


@router.get("/categories", response_model=List[ChecklistCategoryResponse])
async def get_categories(
    db: AsyncSession = Depends(get_db)
):
    """
    Get all checklist categories.
    """
    result = await db.execute(
        select(ChecklistCategory)
        .where(ChecklistCategory.is_active == True)
        .order_by(ChecklistCategory.order)
    )
    categories = result.scalars().all()

    return [ChecklistCategoryResponse.model_validate(cat) for cat in categories]


@router.get("/categories/{category_id}", response_model=ChecklistCategoryWithItems)
async def get_category_with_items(
    category_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific category with all its checklist items and coaching questions.
    """
    result = await db.execute(
        select(ChecklistCategory)
        .where(
            ChecklistCategory.id == category_id,
            ChecklistCategory.is_active == True
        )
        .options(
            selectinload(ChecklistCategory.items).selectinload(ChecklistItem.coaching_questions)
        )
    )
    category = result.scalar_one_or_none()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category with id {category_id} not found"
        )

    return ChecklistCategoryWithItems.model_validate(category)


@router.get("/items", response_model=List[ChecklistItemResponse])
async def get_all_items(
    category_id: int = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all checklist items, optionally filtered by category.
    Returns items with coaching questions.
    """
    query = select(ChecklistItem).where(ChecklistItem.is_active == True)

    if category_id:
        query = query.where(ChecklistItem.category_id == category_id)

    query = query.options(selectinload(ChecklistItem.coaching_questions))
    query = query.order_by(ChecklistItem.category_id, ChecklistItem.order)

    result = await db.execute(query)
    items = result.scalars().all()

    return [ChecklistItemResponse.model_validate(item) for item in items]


@router.get("/items/{item_id}", response_model=ChecklistItemResponse)
async def get_item(
    item_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific checklist item with coaching questions.
    """
    result = await db.execute(
        select(ChecklistItem)
        .where(
            ChecklistItem.id == item_id,
            ChecklistItem.is_active == True
        )
        .options(selectinload(ChecklistItem.coaching_questions))
    )
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Checklist item with id {item_id} not found"
        )

    return ChecklistItemResponse.model_validate(item)


@router.get("/items/{item_id}/behavioral-framework")
async def get_item_behavioral_framework(
    item_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get behavioral framework for a specific checklist item.
    Returns behaviors, questions, coaching areas, and key reminders.

    This endpoint provides the detailed criteria used by AI to evaluate
    the checklist item, including specific questions to look for in transcripts.
    """
    # First, verify the checklist item exists
    item_result = await db.execute(
        select(ChecklistItem)
        .where(
            ChecklistItem.id == item_id,
            ChecklistItem.is_active == True
        )
    )
    item = item_result.scalar_one_or_none()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Checklist item with id {item_id} not found"
        )

    # Fetch behavioral framework using item ID (proper foreign key relationship)
    framework_result = await db.execute(
        select(ChecklistItemBehaviour)
        .where(ChecklistItemBehaviour.checklist_item_id == item_id)
        .where(ChecklistItemBehaviour.isactive == True)
        .order_by(ChecklistItemBehaviour.order)
    )
    framework_rows = framework_result.scalars().all()

    if not framework_rows:
        return {
            "item_id": item_id,
            "item_title": item.title,
            "behavior": None,
            "questions": [],
            "coaching_area": None,
            "key_reminder": None
        }

    # Group by row type
    behavior_row = next((r for r in framework_rows if r.rowtype == 'Behavior'), None)
    question_rows = [r for r in framework_rows if r.rowtype == 'Question']
    reminder_row = next((r for r in framework_rows if r.rowtype == 'Reminder'), None)

    # Get coaching area from first question (they all share the same coaching area)
    coaching_area = question_rows[0].coachingarea if question_rows else None

    return {
        "item_id": item_id,
        "item_title": item.title,
        "item_definition": item.definition,
        "behavior": {
            "summary": behavior_row.behaviour if behavior_row else None,
            "coaching_area": coaching_area
        } if behavior_row else None,
        "questions": [
            {
                "order": q.order,
                "question_text": q.question
            }
            for q in question_rows
        ],
        "coaching_area": coaching_area,
        "key_reminder": reminder_row.keyreminder if reminder_row else None
    }
