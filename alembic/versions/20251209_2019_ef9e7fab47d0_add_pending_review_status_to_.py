"""add_pending_review_status_to_sessionstatus_enum

Revision ID: ef9e7fab47d0
Revises: d1b48e28ecc4
Create Date: 2025-12-09 20:19:20.219204

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ef9e7fab47d0'
down_revision: Union[str, None] = 'd1b48e28ecc4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add 'pending_review' value to sessionstatus enum
    op.execute("ALTER TYPE sessionstatus ADD VALUE IF NOT EXISTS 'pending_review'")


def downgrade() -> None:
    # Note: PostgreSQL does not support removing enum values directly
    # A full downgrade would require recreating the enum type and updating all references
    # For safety, we'll leave this as a no-op
    # If you need to remove it, you'll need to manually recreate the enum
    pass
