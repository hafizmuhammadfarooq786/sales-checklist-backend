"""
Checklist models - The Sales Checklist™ Framework (10 essential items)
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, Float
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin


class ChecklistCategory(Base, TimestampMixin):
    """
    Single checklist category containing all 10 items.
    The system uses a flat structure with one default category.
    """
    __tablename__ = "checklist_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    order = Column(Integer, nullable=False)  # Display order (1-10)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    items = relationship("ChecklistItem", back_populates="category", cascade="all, delete-orphan")


class ChecklistItem(Base, TimestampMixin):
    """
    10 essential checklist items for sales process validation.
    Each item represents a key aspect that must be validated during the sales process.
    """
    __tablename__ = "checklist_items"

    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("checklist_categories.id", ondelete="CASCADE"), nullable=False)

    # Content from client Excel files
    title = Column(String(500), nullable=False)  # Short title
    definition = Column(Text, nullable=False)  # What must be validated

    # Order within category
    order = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    category = relationship("ChecklistCategory", back_populates="items")
    coaching_questions = relationship("CoachingQuestion", back_populates="item", cascade="all, delete-orphan")
    session_responses = relationship("SessionResponse", back_populates="item")
    behaviours = relationship("ChecklistItemBehaviour", back_populates="checklist_item", cascade="all, delete-orphan")


class CoachingQuestion(Base, TimestampMixin):
    """
    Coaching questions for each checklist item (4-8 questions per item)
    """
    __tablename__ = "coaching_questions"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("checklist_items.id", ondelete="CASCADE"), nullable=False)

    section = Column(String(255), nullable=False)  # Section name from Excel
    question = Column(Text, nullable=False)
    order = Column(Integer, nullable=False)

    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    item = relationship("ChecklistItem", back_populates="coaching_questions")
