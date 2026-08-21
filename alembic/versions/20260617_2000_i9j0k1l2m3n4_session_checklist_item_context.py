"""add session checklist item context for knowledge intelligence

Revision ID: i9j0k1l2m3n4
Revises: h8i9j0k1l2m3
Create Date: 2026-06-17 20:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "i9j0k1l2m3n4"
down_revision: Union[str, None] = "h8i9j0k1l2m3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "session_checklist_item_contexts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("checklist_item_id", sa.Integer(), nullable=False),
        sa.Column("deal_context", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["checklist_item_id"], ["checklist_items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "session_id",
            "checklist_item_id",
            name="uq_session_checklist_item_context",
        ),
    )
    op.create_index(
        "ix_session_checklist_item_contexts_session_id",
        "session_checklist_item_contexts",
        ["session_id"],
    )
    op.create_index(
        "ix_session_checklist_item_contexts_checklist_item_id",
        "session_checklist_item_contexts",
        ["checklist_item_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_session_checklist_item_contexts_checklist_item_id",
        table_name="session_checklist_item_contexts",
    )
    op.drop_index(
        "ix_session_checklist_item_contexts_session_id",
        table_name="session_checklist_item_contexts",
    )
    op.drop_table("session_checklist_item_contexts")
