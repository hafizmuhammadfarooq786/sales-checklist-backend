"""organization knowledge base tables

Revision ID: h8i9j0k1l2m3
Revises: g7h8i9j0k1l2
Create Date: 2026-06-17 18:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "h8i9j0k1l2m3"
down_revision: Union[str, None] = "g7h8i9j0k1l2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    kb_status_enum = postgresql.ENUM(
        "not_started",
        "processing",
        "ready",
        "error",
        name="knowledgebasestatus",
        create_type=False,
    )
    doc_status_enum = postgresql.ENUM(
        "queued",
        "processing",
        "indexed",
        "failed",
        name="knowledgedocumentstatus",
        create_type=False,
    )
    kb_status_enum.create(op.get_bind(), checkfirst=True)
    doc_status_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "organization_settings",
        sa.Column(
            "knowledge_base_status",
            kb_status_enum,
            nullable=False,
            server_default="not_started",
        ),
    )
    op.add_column(
        "organization_settings",
        sa.Column("knowledge_base_ready_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "organization_settings",
        sa.Column("knowledge_base_error_message", sa.Text(), nullable=True),
    )

    op.create_table(
        "organization_knowledge_documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("uploaded_by_user_id", sa.Integer(), nullable=True),
        sa.Column("original_filename", sa.String(length=500), nullable=False),
        sa.Column("content_type", sa.String(length=127), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("s3_key", sa.Text(), nullable=False),
        sa.Column("s3_url", sa.Text(), nullable=True),
        sa.Column(
            "status",
            doc_status_enum,
            nullable=False,
            server_default="queued",
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("chunk_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploaded_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_organization_knowledge_documents_organization_id",
        "organization_knowledge_documents",
        ["organization_id"],
    )
    op.create_index(
        "ix_organization_knowledge_documents_status",
        "organization_knowledge_documents",
        ["status"],
    )

    op.create_table(
        "organization_knowledge_chunks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("token_estimate", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["organization_knowledge_documents.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_organization_knowledge_chunks_organization_id",
        "organization_knowledge_chunks",
        ["organization_id"],
    )
    op.create_index(
        "ix_organization_knowledge_chunks_document_id",
        "organization_knowledge_chunks",
        ["document_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_organization_knowledge_chunks_document_id",
        table_name="organization_knowledge_chunks",
    )
    op.drop_index(
        "ix_organization_knowledge_chunks_organization_id",
        table_name="organization_knowledge_chunks",
    )
    op.drop_table("organization_knowledge_chunks")

    op.drop_index(
        "ix_organization_knowledge_documents_status",
        table_name="organization_knowledge_documents",
    )
    op.drop_index(
        "ix_organization_knowledge_documents_organization_id",
        table_name="organization_knowledge_documents",
    )
    op.drop_table("organization_knowledge_documents")

    op.drop_column("organization_settings", "knowledge_base_error_message")
    op.drop_column("organization_settings", "knowledge_base_ready_at")
    op.drop_column("organization_settings", "knowledge_base_status")

    op.execute("DROP TYPE IF EXISTS knowledgedocumentstatus")
    op.execute("DROP TYPE IF EXISTS knowledgebasestatus")
