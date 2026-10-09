"""session shares for read-only salesperson access

Revision ID: r8s9t0u1v2w3
Revises: q7r8s9t0u1v2
Create Date: 2026-10-09 16:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "r8s9t0u1v2w3"
down_revision: Union[str, None] = "q7r8s9t0u1v2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "session_shares",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("permission", sa.String(length=16), nullable=False, server_default="read"),
        sa.Column("added_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["added_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("session_id", "user_id", name="uq_session_shares_session_user"),
    )
    op.create_index("ix_session_shares_session_id", "session_shares", ["session_id"])
    op.create_index("ix_session_shares_user_id", "session_shares", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_session_shares_user_id", table_name="session_shares")
    op.drop_index("ix_session_shares_session_id", table_name="session_shares")
    op.drop_table("session_shares")
