"""add structured_content JSONB to checklist_item_notes

Revision ID: a1d9e4b2c801
Revises: 8b4d2e1f9c00
Create Date: 2026-04-01 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "a1d9e4b2c801"
down_revision: Union[str, None] = "8b4d2e1f9c00"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("checklist_item_notes"):
        return
    cols = {c["name"] for c in inspector.get_columns("checklist_item_notes")}
    if "structured_content" not in cols:
        op.add_column(
            "checklist_item_notes",
            sa.Column(
                "structured_content",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=True,
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("checklist_item_notes"):
        return
    cols = {c["name"] for c in inspector.get_columns("checklist_item_notes")}
    if "structured_content" in cols:
        op.drop_column("checklist_item_notes", "structured_content")
