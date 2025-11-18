"""
Checklist models - Sales Checklist™ Framework (92 items)
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, Float
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin


class ChecklistCategory(Base, TimestampMixin):
    """
    10 main checklist categories
    Examples: Trigger Event, Priority, Target, Decision Influencer, etc.
    """
    __tablename__ = "checklist_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    order = Column(Integer, nullable=False)  # Display order (1-10)

    # Scoring
    default_weight = Column(Float, default=1.0)  # For weighted scoring
    max_score = Column(Integer, default=10)  # Max points for this category

    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    items = relationship("ChecklistItem", back_populates="category", cascade="all, delete-orphan")


class ChecklistItem(Base, TimestampMixin):
    """
    92 individual checklist items across 10 categories
    """
    __tablename__ = "checklist_items"

    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("checklist_categories.id", ondelete="CASCADE"), nullable=False)

    # Content from client Excel files
    title = Column(String(500), nullable=False)  # Short title
    definition = Column(Text, nullable=False)  # What must be validated
    key_behavior = Column(Text, nullable=True)  # Key Salesperson Behavior
    key_mindset = Column(Text, nullable=True)  # Strategic perspective

    # Order within category
    order = Column(Integer, nullable=False)

    # Scoring configuration
    weight = Column(Float, default=1.0)  # Item-specific weight
    points = Column(Float, default=1.087)  # Default: 100/92 = 1.087 points

    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    category = relationship("ChecklistCategory", back_populates="items")
    coaching_questions = relationship("CoachingQuestion", back_populates="item", cascade="all, delete-orphan")
    session_responses = relationship("SessionResponse", back_populates="item")


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
