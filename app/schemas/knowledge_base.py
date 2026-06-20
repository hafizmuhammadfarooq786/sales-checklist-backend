"""Pydantic schemas for Organization Knowledge Intelligence."""
from datetime import datetime
from typing import List, Optional, Any

from pydantic import BaseModel, Field, field_validator


class KnowledgeBaseStatusResponse(BaseModel):
    status: str
    is_enabled: bool
    indexed_document_count: int
    total_document_count: int
    min_documents_required: int
    ready_at: Optional[datetime] = None
    error_message: Optional[str] = None


class KnowledgeDocumentResponse(BaseModel):
    id: int
    organization_id: int
    original_filename: str
    content_type: str
    file_size_bytes: int
    status: str
    error_message: Optional[str] = None
    chunk_count: int
    uploaded_by_user_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, value: Any) -> str:
        if hasattr(value, "value"):
            return value.value
        return str(value)

    class Config:
        from_attributes = True


class KnowledgeDocumentUploadResponse(BaseModel):
    document: KnowledgeDocumentResponse
    message: str


class KnowledgeAskRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=2000)


class KnowledgeCitation(BaseModel):
    document_id: int
    document_name: str
    excerpt: str


class KnowledgeAskResponse(BaseModel):
    answer: str
    citations: List[KnowledgeCitation]
    knowledge_base_enabled: bool


class ChecklistItemContextUpdate(BaseModel):
    deal_context: str = Field("", max_length=2000)


class ChecklistItemContextResponse(BaseModel):
    session_id: int
    checklist_item_id: int
    deal_context: Optional[str] = None


class SessionChecklistContextsResponse(BaseModel):
    session_id: int
    contexts: List[ChecklistItemContextResponse]


class ChecklistItemIntelligenceRequest(BaseModel):
    deal_context: Optional[str] = Field(None, max_length=2000)


class ChecklistItemIntelligenceResponse(BaseModel):
    knowledge_base_enabled: bool
    expertise_points: List[str]
    yes_guidance: str
    no_guidance: str
    citations: List[KnowledgeCitation]


class NextBestAnswer(BaseModel):
    title: str
    action: str
    rationale: str
    checklist_item_order: Optional[int] = None


class EmbeddedCoachingItem(BaseModel):
    checklist_item_order: Optional[int] = None
    prompts: List[str] = Field(default_factory=list)


class TechnicalRiskItem(BaseModel):
    title: str
    severity: str
    description: str
    checklist_item_orders: List[int] = Field(default_factory=list)


class SessionKnowledgeInsightResponse(BaseModel):
    knowledge_base_enabled: bool
    next_best_answers: List[NextBestAnswer] = Field(default_factory=list)
    embedded_coaching: List[EmbeddedCoachingItem] = Field(default_factory=list)
    technical_risks: List[TechnicalRiskItem] = Field(default_factory=list)
    summary_text: Optional[str] = None
    has_technical_risk: bool = False
    analyzed_at: Optional[datetime] = None


class EmbeddedCoachingRequest(BaseModel):
    checklist_item_id: int
    trigger: str = Field(default="no", pattern="^(no|help|low_score)$")
    deal_context: Optional[str] = Field(None, max_length=2000)


class EmbeddedCoachingResponse(BaseModel):
    knowledge_base_enabled: bool
    checklist_item_id: int
    trigger: str
    prompts: List[str]


class SellingToolRequest(BaseModel):
    tool_type: str = Field(
        ...,
        pattern="^(executive_summary|contractor_talking_points|architect_summary|objection_handling|battle_card|roi_summary)$",
    )


class SellingToolResponse(BaseModel):
    knowledge_base_enabled: bool
    tool_type: str
    tool_label: str
    content: str
    document_id: int
    document_name: str
