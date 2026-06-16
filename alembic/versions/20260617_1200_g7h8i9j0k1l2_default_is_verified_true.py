"""default is_verified to true for users

Revision ID: g7h8i9j0k1l2
Revises: f6a7b8c9d0e1
Create Date: 2026-06-17 12:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "g7h8i9j0k1l2"
down_revision: Union[str, None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE users SET is_verified = true WHERE is_verified = false")
    op.alter_column(
        "users",
        "is_verified",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "users",
        "is_verified",
        existing_type=sa.Boolean(),
        server_default=sa.text("false"),
        nullable=False,
    )
