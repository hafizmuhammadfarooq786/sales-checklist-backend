"""
Pydantic schemas for Checklist endpoints
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class CoachingQuestionBase(BaseModel):
    """Base schema for coaching questions"""
    section: str
    question: str
    order: int


class CoachingQuestionResponse(CoachingQuestionBase):
    """Response schema for coaching questions"""
    id: int
    item_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChecklistItemBase(BaseModel):
    """Base schema for checklist items"""
    title: str
    definition: str
    key_behavior: Optional[str] = None
    key_mindset: Optional[str] = None
    order: int
    weight: float = 1.0
    points: float = 1.087


class ChecklistItemResponse(ChecklistItemBase):
    """Response schema for checklist items"""
    id: int
    category_id: int
    is_active: bool
    coaching_questions: List[CoachingQuestionResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChecklistCategoryBase(BaseModel):
    """Base schema for checklist categories"""
    name: str
    description: Optional[str] = None
    order: int
    default_weight: float = 1.0
    max_score: int = 10


class ChecklistCategoryResponse(ChecklistCategoryBase):
    """Response schema for checklist categories"""
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChecklistCategoryWithItems(ChecklistCategoryResponse):
    """Response schema for category with all items"""
    items: List[ChecklistItemResponse] = []

    class Config:
        from_attributes = True


class ChecklistSummary(BaseModel):
    """Summary of all checklists"""
    total_categories: int
    total_items: int
    categories: List[ChecklistCategoryResponse]
