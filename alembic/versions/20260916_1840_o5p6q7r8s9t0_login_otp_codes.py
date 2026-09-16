"""Create login_otp_codes table for passwordless OTP sign-in

Revision ID: o5p6q7r8s9t0
Revises: n4o5p6q7r8s9
Create Date: 2026-09-16 18:40:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "o5p6q7r8s9t0"
down_revision: Union[str, None] = "n4o5p6q7r8s9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "login_otp_codes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_login_otp_codes_user_id", "login_otp_codes", ["user_id"])
    op.create_index("ix_login_otp_codes_expires_at", "login_otp_codes", ["expires_at"])
    op.create_index("ix_login_otp_codes_revoked_at", "login_otp_codes", ["revoked_at"])
    op.create_index("ix_login_otp_codes_created_at", "login_otp_codes", ["created_at"])
    op.create_index(
        "ix_login_otp_codes_user_active",
        "login_otp_codes",
        ["user_id", "revoked_at", "expires_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_login_otp_codes_user_active", table_name="login_otp_codes")
    op.drop_index("ix_login_otp_codes_created_at", table_name="login_otp_codes")
    op.drop_index("ix_login_otp_codes_revoked_at", table_name="login_otp_codes")
    op.drop_index("ix_login_otp_codes_expires_at", table_name="login_otp_codes")
    op.drop_index("ix_login_otp_codes_user_id", table_name="login_otp_codes")
    op.drop_table("login_otp_codes")
