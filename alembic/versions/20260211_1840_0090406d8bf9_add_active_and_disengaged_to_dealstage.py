"""add_active_and_disengaged_to_dealstage

Revision ID: 0090406d8bf9
Revises: 6e34883e7810
Create Date: 2026-02-11 18:40:09.869971

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0090406d8bf9'
down_revision: Union[str, None] = '6e34883e7810'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new values to existing dealstage enum
    op.execute("ALTER TYPE dealstage ADD VALUE IF NOT EXISTS 'active'")
    op.execute("ALTER TYPE dealstage ADD VALUE IF NOT EXISTS 'disengaged'")


def downgrade() -> None:
    # PostgreSQL doesn't support removing enum values directly
    # Would need to recreate the enum type to remove values
    # Since this is additive only, we'll leave the values in place
    pass
