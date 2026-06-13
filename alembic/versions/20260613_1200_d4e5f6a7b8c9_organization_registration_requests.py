"""organization registration requests for public signup approval

Revision ID: d4e5f6a7b8c9
Revises: c3d8e1f2a4b5
Create Date: 2026-06-13 12:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c3d8e1f2a4b5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    status_enum = postgresql.ENUM(
        "pending",
        "approved",
        "rejected",
        name="organizationregistrationstatus",
        create_type=False,
    )
    status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "organization_registration_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            status_enum,
            nullable=False,
            server_default="pending",
        ),
        sa.Column("company_name", sa.String(length=255), nullable=False),
        sa.Column("industry", sa.String(length=100), nullable=False),
        sa.Column("logo_url", sa.Text(), nullable=True),
        sa.Column("admin_first_name", sa.String(length=100), nullable=False),
        sa.Column("admin_last_name", sa.String(length=100), nullable=False),
        sa.Column("admin_email", sa.String(length=255), nullable=False),
        sa.Column("admin_direct_dial", sa.String(length=50), nullable=False),
        sa.Column("admin_cell_phone", sa.String(length=50), nullable=True),
        sa.Column(
            "additional_users",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column("organization_id", sa.Integer(), nullable=True),
        sa.Column("reviewed_by", sa.Integer(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_organization_registration_requests_id"),
        "organization_registration_requests",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_organization_registration_requests_status"),
        "organization_registration_requests",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_organization_registration_requests_admin_email"),
        "organization_registration_requests",
        ["admin_email"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_organization_registration_requests_admin_email"),
        table_name="organization_registration_requests",
    )
    op.drop_index(
        op.f("ix_organization_registration_requests_status"),
        table_name="organization_registration_requests",
    )
    op.drop_index(
        op.f("ix_organization_registration_requests_id"),
        table_name="organization_registration_requests",
    )
    op.drop_table("organization_registration_requests")
    op.execute("DROP TYPE IF EXISTS organizationregistrationstatus")
