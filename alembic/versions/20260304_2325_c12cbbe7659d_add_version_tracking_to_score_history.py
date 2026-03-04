"""add_version_tracking_to_score_history

Adds versioning capabilities to score_history table:
- version_number: Sequential version counter (1, 2, 3, etc.)
- changes_count: Number of checklist items changed from previous version
- responses_snapshot: Complete JSON snapshot of all checklist responses

This enables full version history for sessions, allowing users to:
1. View exactly what the checklist looked like at each submission
2. Track progression of deals over time
3. Compare changes between versions

Revision ID: c12cbbe7659d
Revises: 81940ba18b42
Create Date: 2026-03-04 23:25:26.009324

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'c12cbbe7659d'
down_revision: Union[str, None] = '81940ba18b42'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add version tracking columns to score_history table.
    """
    # Add version_number column (required, defaults to 1 for existing records)
    op.add_column('score_history',
        sa.Column('version_number', sa.Integer(), nullable=False, server_default='1')
    )

    # Add changes_count column (optional, tracks how many items changed)
    op.add_column('score_history',
        sa.Column('changes_count', sa.Integer(), nullable=True)
    )

    # Add responses_snapshot column (required, stores complete checklist state)
    # For existing records, set empty array as default
    op.add_column('score_history',
        sa.Column('responses_snapshot', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='[]')
    )

    # Remove server defaults after backfilling existing data
    op.alter_column('score_history', 'version_number', server_default=None)
    op.alter_column('score_history', 'responses_snapshot', server_default=None)

    # Create index on version_number for faster queries
    op.create_index('idx_score_history_version', 'score_history', ['session_id', 'version_number'], unique=True)


def downgrade() -> None:
    """
    Remove version tracking columns from score_history table.
    """
    # Drop index
    op.drop_index('idx_score_history_version', table_name='score_history')

    # Drop columns
    op.drop_column('score_history', 'responses_snapshot')
    op.drop_column('score_history', 'changes_count')
    op.drop_column('score_history', 'version_number')
