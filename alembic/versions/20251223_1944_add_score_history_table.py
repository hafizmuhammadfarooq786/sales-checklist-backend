"""add_score_history_table

Revision ID: 7f8a9b0c1d2e
Revises: 12b3e1095b59
Create Date: 2025-12-23 19:44:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '7f8a9b0c1d2e'
down_revision: Union[str, None] = '12b3e1095b59'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Create score_history table to track all score calculations over time.
    This preserves historical score data when users edit AI answers and recalculate.
    """
    # Create score_history table
    op.create_table(
        'score_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('scoring_result_id', sa.Integer(), nullable=True),
        sa.Column('total_score', sa.Float(), nullable=False),
        sa.Column('risk_band', sa.String(length=20), nullable=False),
        sa.Column('items_validated', sa.Integer(), nullable=False),
        sa.Column('items_total', sa.Integer(), nullable=False),
        sa.Column('calculated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('score_change', sa.Float(), nullable=True),
        sa.Column('trigger_event', sa.String(length=100), nullable=True),
        sa.Column('created_by_user_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for performance
    op.create_index('idx_score_history_session_id', 'score_history', ['session_id'])
    op.create_index('idx_score_history_calculated_at', 'score_history', ['calculated_at'], postgresql_ops={'calculated_at': 'DESC'})
    op.create_index('idx_score_history_scoring_result_id', 'score_history', ['scoring_result_id'])

    # Create foreign key constraints
    op.create_foreign_key(
        'fk_score_history_session_id',
        'score_history',
        'sessions',
        ['session_id'],
        ['id'],
        ondelete='CASCADE'
    )

    op.create_foreign_key(
        'fk_score_history_scoring_result_id',
        'score_history',
        'scoring_results',
        ['scoring_result_id'],
        ['id'],
        ondelete='SET NULL'
    )

    op.create_foreign_key(
        'fk_score_history_created_by_user_id',
        'score_history',
        'users',
        ['created_by_user_id'],
        ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    """
    Remove score_history table and all associated indexes and constraints.
    """
    # Drop foreign key constraints
    op.drop_constraint('fk_score_history_created_by_user_id', 'score_history', type_='foreignkey')
    op.drop_constraint('fk_score_history_scoring_result_id', 'score_history', type_='foreignkey')
    op.drop_constraint('fk_score_history_session_id', 'score_history', type_='foreignkey')

    # Drop indexes
    op.drop_index('idx_score_history_scoring_result_id', table_name='score_history')
    op.drop_index('idx_score_history_calculated_at', table_name='score_history')
    op.drop_index('idx_score_history_session_id', table_name='score_history')

    # Drop table
    op.drop_table('score_history')
