"""organization partners for cross-company checklist sharing

Revision ID: s9t0u1v2w3x4
Revises: r8s9t0u1v2w3
Create Date: 2026-11-03 10:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "s9t0u1v2w3x4"
down_revision: Union[str, None] = "r8s9t0u1v2w3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "organization_partners",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("a_id", sa.Integer(), nullable=False),
        sa.Column("b_id", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["a_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["b_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("a_id", "b_id", name="uq_organization_partners_pair"),
        # Pairs are stored lower id first, so each appears once; this also stops
        # an organization being partnered with itself.
        sa.CheckConstraint("a_id < b_id", name="ck_organization_partners_ordered"),
    )
    op.create_index("ix_organization_partners_a_id", "organization_partners", ["a_id"])
    op.create_index("ix_organization_partners_b_id", "organization_partners", ["b_id"])


def downgrade() -> None:
    op.drop_index("ix_organization_partners_b_id", table_name="organization_partners")
    op.drop_index("ix_organization_partners_a_id", table_name="organization_partners")
    op.drop_table("organization_partners")
