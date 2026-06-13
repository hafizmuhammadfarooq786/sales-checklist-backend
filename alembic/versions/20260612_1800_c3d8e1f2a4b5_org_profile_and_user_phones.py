"""org profile fields, executive sponsor, user phones, EXECUTIVE role

Revision ID: c3d8e1f2a4b5
Revises: b8e4f1a2c3d4
Create Date: 2026-06-12 18:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c3d8e1f2a4b5"
down_revision: Union[str, None] = "b8e4f1a2c3d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("organizations", sa.Column("industry", sa.String(length=100), nullable=True))

    op.add_column(
        "organization_settings",
        sa.Column("executive_sponsor_name", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "organization_settings",
        sa.Column("executive_sponsor_email", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "organization_settings",
        sa.Column("executive_sponsor_direct_dial", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "organization_settings",
        sa.Column("executive_sponsor_cell_phone", sa.String(length=50), nullable=True),
    )

    op.add_column("users", sa.Column("direct_dial", sa.String(length=50), nullable=True))
    op.add_column("users", sa.Column("cell_phone", sa.String(length=50), nullable=True))

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_enum
                WHERE enumlabel = 'EXECUTIVE'
                AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'userrole')
            ) THEN
                ALTER TYPE userrole ADD VALUE 'EXECUTIVE';
            END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    op.drop_column("users", "cell_phone")
    op.drop_column("users", "direct_dial")
    op.drop_column("organization_settings", "executive_sponsor_cell_phone")
    op.drop_column("organization_settings", "executive_sponsor_direct_dial")
    op.drop_column("organization_settings", "executive_sponsor_email")
    op.drop_column("organization_settings", "executive_sponsor_name")
    op.drop_column("organizations", "industry")
