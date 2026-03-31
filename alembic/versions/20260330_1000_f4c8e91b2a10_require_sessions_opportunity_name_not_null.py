"""require sessions.opportunity_name NOT NULL

Revision ID: f4c8e91b2a10
Revises: 2f1ebf5f8086
Create Date: 2026-03-30 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f4c8e91b2a10"
down_revision: Union[str, None] = "2f1ebf5f8086"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Backfill NULL or whitespace-only values from customer_name (required on sessions).
    op.execute(
        """
        UPDATE sessions
        SET opportunity_name = TRIM(customer_name)
        WHERE opportunity_name IS NULL OR TRIM(opportunity_name) = '';
        """
    )
    op.alter_column(
        "sessions",
        "opportunity_name",
        existing_type=sa.String(length=255),
        nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "sessions",
        "opportunity_name",
        existing_type=sa.String(length=255),
        nullable=True,
    )
