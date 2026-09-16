"""Drop password columns now that sign-in is OTP-only

Revision ID: p6q7r8s9t0u1
Revises: o5p6q7r8s9t0
Create Date: 2026-09-16 19:45:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "p6q7r8s9t0u1"
down_revision: Union[str, None] = "o5p6q7r8s9t0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("users", "must_change_password")
    op.drop_column("users", "password_reset_expires")
    op.drop_column("users", "password_reset_token")
    op.drop_column("users", "password_hash")


def downgrade() -> None:
    op.add_column("users", sa.Column("password_hash", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("password_reset_token", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("password_reset_expires", sa.DateTime(), nullable=True))
    op.add_column(
        "users",
        sa.Column("must_change_password", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.execute("UPDATE users SET password_hash = 'otp_only_placeholder' WHERE password_hash IS NULL")
    op.alter_column("users", "password_hash", nullable=False)
    op.alter_column("users", "must_change_password", server_default=None)
