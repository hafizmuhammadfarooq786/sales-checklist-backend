"""add_manager_notes_table

Revision ID: 7ec002909a00
Revises: e50261cf48cd
Create Date: 2026-02-03 22:49:48.622580

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7ec002909a00'
down_revision: Union[str, None] = 'e50261cf48cd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create manager_notes table
    op.create_table(
        'manager_notes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('manager_id', sa.Integer(), nullable=False),
        sa.Column('note_text', sa.Text(), nullable=False),
        sa.Column('is_edited', sa.Boolean(), default=False, nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['manager_id'], ['users.id'], ondelete='CASCADE'),
    )

    # Create indexes for better query performance
    op.create_index('idx_manager_notes_session_id', 'manager_notes', ['session_id'])
    op.create_index('idx_manager_notes_manager_id', 'manager_notes', ['manager_id'])
    op.create_index('idx_manager_notes_created_at', 'manager_notes', ['created_at'])


def downgrade() -> None:
    op.drop_index('idx_manager_notes_created_at')
    op.drop_index('idx_manager_notes_manager_id')
    op.drop_index('idx_manager_notes_session_id')
    op.drop_table('manager_notes')
