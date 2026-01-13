"""add session_mode to sessions table

Revision ID: 20251230_1500
Revises: 20251224_1200
Create Date: 2025-12-30 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20251230_1500'
down_revision: Union[str, None] = '20251224_1200'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add session_mode column to sessions table
    # Default to 'AUDIO' (uppercase) for backward compatibility with existing sessions
    # Note: Must use uppercase to match SessionMode enum values
    op.add_column(
        'sessions',
        sa.Column('session_mode', sa.String(20), nullable=False, server_default='AUDIO')
    )

    # Create index for querying by mode (useful for analytics)
    op.create_index('idx_sessions_mode', 'sessions', ['session_mode'])


def downgrade() -> None:
    # Drop index first
    op.drop_index('idx_sessions_mode', 'sessions')

    # Drop column
    op.drop_column('sessions', 'session_mode')
