"""
Checklist Behavioral Framework models
Stores detailed behavioral criteria and questions for each checklist item
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, Float, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base


class ChecklistItemBehaviour(Base):
    """
    Behavioral framework for checklist items.
    Stores behaviors, questions, coaching areas, and key reminders from JSON files.
    """
    __tablename__ = "checklist_item_behaviours"

    id = Column(Integer, primary_key=True, index=True)

    # Foreign key to checklist_items (proper relational link)
    checklist_item_id = Column(Integer, ForeignKey("checklist_items.id", ondelete="CASCADE"), nullable=False, index=True)

    # From JSON: ChecklistItemName (kept for reference, but now use ID for queries)
    checklistitemname = Column(String(255), nullable=False, index=True)

    # From JSON: RowType ('Behavior', 'Question', 'Reminder')
    rowtype = Column(String(20), nullable=False, index=True)

    # From JSON: CoachingArea
    coachingarea = Column(String(100), nullable=True)

    # From JSON: QuestionOrder
    order = Column("order", Integer, nullable=False, default=0)

    # From JSON: QuestionText
    question = Column(Text, nullable=True)

    # From JSON: BehaviorSummary
    behaviour = Column(Text, nullable=True)

    # From JSON: KeyReminder
    keyreminder = Column(Text, nullable=True)

    # From JSON: IsActive
    isactive = Column(Boolean, nullable=False, default=True, index=True)

    # Timestamps
    createdat = Column(TIMESTAMP, nullable=False, server_default=func.now())
    updatedat = Column(TIMESTAMP, nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    checklist_item = relationship("ChecklistItem", back_populates="behaviours")
    analyses = relationship("SessionResponseAnalysis", back_populates="behaviour", cascade="all, delete-orphan")


class SessionResponseAnalysis(Base):
    """
    Per-question AI evaluation for each session response.
    Links to specific questions via behaviour_id.
    """
    __tablename__ = "session_response_analysis"

    id = Column(Integer, primary_key=True, index=True)

    # Foreign keys
    session_response_id = Column(
        Integer,
        ForeignKey("session_responses.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    behaviour_id = Column(
        Integer,
        ForeignKey("checklist_item_behaviours.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Question evaluation results
    evidence_found = Column(Boolean, nullable=False, default=False, index=True)
    evidence_text = Column(Text, nullable=True)
    ai_reasoning = Column(Text, nullable=True)
    confidence_score = Column(Float, nullable=True)

    # Timestamp
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())

    # Relationships
    session_response = relationship("SessionResponse", back_populates="question_analyses")
    behaviour = relationship("ChecklistItemBehaviour", back_populates="analyses")
