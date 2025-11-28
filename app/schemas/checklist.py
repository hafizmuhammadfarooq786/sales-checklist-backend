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


# ============================================================================
# NEW SCHEMAS FOR CHECKLIST REVIEW (10-item AI auto-fill system)
# ============================================================================

class ChecklistItemInfo(BaseModel):
    """Simplified checklist item info for review page"""
    id: int
    title: str
    definition: str
    key_behavior: Optional[str] = None
    order: int

    class Config:
        from_attributes = True


class CoachingQuestionInfo(BaseModel):
    """Simplified coaching question for review page"""
    id: int
    section: str
    question: str
    order: int

    class Config:
        from_attributes = True


class SessionResponseReview(BaseModel):
    """A single checklist item response for review (AI + user answers)"""
    item: ChecklistItemInfo
    ai_answer: bool  # True = Yes (10 pts), False = No (0 pts)
    ai_reasoning: str
    user_answer: Optional[bool] = None  # User's override answer if changed
    was_changed: bool = False
    score: int  # Current score: 0 or 10
    coaching_questions: List[CoachingQuestionInfo] = []

    class Config:
        from_attributes = True


class ChecklistReviewResponse(BaseModel):
    """Complete checklist review for a session (all 10 items)"""
    session_id: int
    customer_name: str
    opportunity_name: Optional[str] = None
    items: List[SessionResponseReview]
    total_score: int  # Sum of all scores (0-100)
    items_yes: int  # Count of YES answers (0-10)
    items_no: int  # Count of NO answers (0-10)
    status: str  # Session status (e.g., "pending_review", "submitted")

    class Config:
        from_attributes = True


class ChecklistItemUpdate(BaseModel):
    """Schema for updating a single checklist item (manual override)"""
    user_answer: bool = Field(..., description="User's answer: True = Yes, False = No")


class ChecklistItemUpdateResponse(BaseModel):
    """Response after updating a single item"""
    item_id: int
    ai_answer: bool
    user_answer: bool
    was_changed: bool
    score: int
    message: str

    class Config:
        from_attributes = True


class ChecklistSubmitResponse(BaseModel):
    """Response after submitting finalized checklist"""
    session_id: int
    total_score: int
    items_yes: int
    items_no: int
    submitted_at: datetime
    message: str

    class Config:
        from_attributes = True
