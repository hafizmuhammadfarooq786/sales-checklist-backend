"""
Organization Knowledge Base models — per-tenant document storage and RAG chunks.
"""
import enum

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    ForeignKey,
    Enum as SQLEnum,
    BigInteger,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin


class KnowledgeBaseStatus(str, enum.Enum):
    """Org-level knowledge base activation state."""

    NOT_STARTED = "not_started"
    PROCESSING = "processing"
    READY = "ready"
    ERROR = "error"


class KnowledgeDocumentStatus(str, enum.Enum):
    """Per-document ingestion lifecycle."""

    QUEUED = "queued"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"


class OrganizationKnowledgeDocument(Base, TimestampMixin):
    """Uploaded knowledge document for an organization."""

    __tablename__ = "organization_knowledge_documents"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    uploaded_by_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    original_filename = Column(String(500), nullable=False)
    content_type = Column(String(127), nullable=False)
    file_size_bytes = Column(BigInteger, nullable=False, default=0)
    s3_key = Column(Text, nullable=False)
    s3_url = Column(Text, nullable=True)

    status = Column(
        SQLEnum(
            KnowledgeDocumentStatus,
            name="knowledgedocumentstatus",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=KnowledgeDocumentStatus.QUEUED,
        index=True,
    )
    error_message = Column(Text, nullable=True)
    chunk_count = Column(Integer, nullable=False, default=0)

    organization = relationship("Organization", backref="knowledge_documents")
    uploaded_by = relationship("User", foreign_keys=[uploaded_by_user_id])
    chunks = relationship(
        "OrganizationKnowledgeChunk",
        back_populates="document",
        cascade="all, delete-orphan",
    )


class OrganizationKnowledgeChunk(Base, TimestampMixin):
    """Text chunk + embedding for semantic retrieval."""

    __tablename__ = "organization_knowledge_chunks"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_id = Column(
        Integer,
        ForeignKey("organization_knowledge_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    chunk_index = Column(Integer, nullable=False, default=0)
    content = Column(Text, nullable=False)
    embedding = Column(JSONB, nullable=True)
    token_estimate = Column(Integer, nullable=True)

    document = relationship("OrganizationKnowledgeDocument", back_populates="chunks")
