"""add_uppercase_PENDING_REVIEW_to_sessionstatus

Revision ID: 475e7ea9f0bc
Revises: ef9e7fab47d0
Create Date: 2025-12-09 23:25:35.345140

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '475e7ea9f0bc'
down_revision: Union[str, None] = 'ef9e7fab47d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add 'PENDING_REVIEW' value (uppercase) to sessionstatus enum to match existing enum values
    op.execute("ALTER TYPE sessionstatus ADD VALUE IF NOT EXISTS 'PENDING_REVIEW'")


def downgrade() -> None:
    pass
