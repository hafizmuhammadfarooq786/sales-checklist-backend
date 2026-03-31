"""add checklist_item_notes (opportunity-scoped versioned notes)

Revision ID: 8b4d2e1f9c00
Revises: f4c8e91b2a10
Create Date: 2026-03-31 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "8b4d2e1f9c00"
down_revision: Union[str, None] = "f4c8e91b2a10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("checklist_item_notes"):
        op.create_table(
            "checklist_item_notes",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("checklist_item_id", sa.Integer(), nullable=False),
            sa.Column("session_id", sa.Integer(), nullable=True),
            sa.Column("customer_name", sa.String(length=255), nullable=False),
            sa.Column("opportunity_name", sa.String(length=255), nullable=False),
            sa.Column("opportunity_key", sa.String(length=64), nullable=False),
            sa.Column("note_text", sa.Text(), nullable=True),
            sa.Column("decision_influencers", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("created_by_user_id", sa.Integer(), nullable=True),
            sa.Column("updated_by_user_id", sa.Integer(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("version", sa.Integer(), nullable=False),
            sa.Column("previous_version_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(
                ["checklist_item_id"], ["checklist_items.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(
                ["previous_version_id"], ["checklist_item_notes.id"], ondelete="SET NULL"
            ),
            sa.PrimaryKeyConstraint("id"),
        )

    # Idempotent indexes (safe if table pre-existed from a partial run)
    op.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS ix_checklist_item_notes_checklist_item_id "
            "ON checklist_item_notes (checklist_item_id)"
        )
    )
    op.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS ix_checklist_item_notes_session_id "
            "ON checklist_item_notes (session_id)"
        )
    )
    op.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS ix_checklist_item_notes_opportunity_key "
            "ON checklist_item_notes (opportunity_key)"
        )
    )
    op.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS ix_checklist_item_notes_opp_item "
            "ON checklist_item_notes (opportunity_key, checklist_item_id)"
        )
    )
    op.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS ix_checklist_item_notes_updated_at "
            "ON checklist_item_notes (updated_at)"
        )
    )
    op.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS ix_checklist_item_notes_created_by_user_id "
            "ON checklist_item_notes (created_by_user_id)"
        )
    )
    op.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS ix_checklist_item_notes_version_lookup "
            "ON checklist_item_notes (checklist_item_id, opportunity_key, version)"
        )
    )
    op.execute(
        sa.text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_checklist_item_notes_active_per_item_opportunity "
            "ON checklist_item_notes (checklist_item_id, opportunity_key) "
            "WHERE is_active = true"
        )
    )


def downgrade() -> None:
    for name in (
        "uq_checklist_item_notes_active_per_item_opportunity",
        "ix_checklist_item_notes_version_lookup",
        "ix_checklist_item_notes_created_by_user_id",
        "ix_checklist_item_notes_updated_at",
        "ix_checklist_item_notes_opp_item",
        "ix_checklist_item_notes_opportunity_key",
        "ix_checklist_item_notes_session_id",
        "ix_checklist_item_notes_checklist_item_id",
    ):
        op.execute(sa.text(f"DROP INDEX IF EXISTS {name}"))
    op.drop_table("checklist_item_notes")
