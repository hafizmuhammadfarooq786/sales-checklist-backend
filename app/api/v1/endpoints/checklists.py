"""
Checklist API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List

from app.db.session import get_db
from app.models import ChecklistCategory, ChecklistItem
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
