"""fix_session_mode_enum_values

Revision ID: e50261cf48cd
Revises: 20251230_1500
Create Date: 2026-01-13 14:54:10.919863

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e50261cf48cd'
down_revision: Union[str, None] = '20251230_1500'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Update existing lowercase values to uppercase to match enum
    op.execute("UPDATE sessions SET session_mode = 'AUDIO' WHERE session_mode = 'audio'")
    op.execute("UPDATE sessions SET session_mode = 'MANUAL' WHERE session_mode = 'manual'")


def downgrade() -> None:
    # Convert back to lowercase
    op.execute("UPDATE sessions SET session_mode = 'audio' WHERE session_mode = 'AUDIO'")
    op.execute("UPDATE sessions SET session_mode = 'manual' WHERE session_mode = 'MANUAL'")
