"""add_behavioral_framework_tables

Revision ID: a1b2c3d4e5f6
Revises: 3f261ae91eb1
Create Date: 2025-12-17 00:39:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '3f261ae91eb1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create checklist_item_behaviours table
    op.create_table(
        'checklist_item_behaviours',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('checklistitemname', sa.String(length=255), nullable=False),
        sa.Column('rowtype', sa.String(length=20), nullable=False),
        sa.Column('coachingarea', sa.String(length=100), nullable=True),
        sa.Column('order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('question', sa.Text(), nullable=True),
        sa.Column('behaviour', sa.Text(), nullable=True),
        sa.Column('keyreminder', sa.Text(), nullable=True),
        sa.Column('isactive', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('createdat', sa.TIMESTAMP(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updatedat', sa.TIMESTAMP(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for checklist_item_behaviours
    op.create_index('idx_cib_checklistitemname', 'checklist_item_behaviours', ['checklistitemname'])
    op.create_index('idx_cib_rowtype', 'checklist_item_behaviours', ['rowtype'])
    op.create_index('idx_cib_isactive', 'checklist_item_behaviours', ['isactive'])

    # Create session_response_analysis table
    op.create_table(
        'session_response_analysis',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_response_id', sa.Integer(), nullable=False),
        sa.Column('behaviour_id', sa.Integer(), nullable=False),
        sa.Column('evidence_found', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('evidence_text', sa.Text(), nullable=True),
        sa.Column('ai_reasoning', sa.Text(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['session_response_id'], ['session_responses.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['behaviour_id'], ['checklist_item_behaviours.id'], ondelete='CASCADE')
    )

    # Create indexes for session_response_analysis
    op.create_index('idx_sra_session_response_id', 'session_response_analysis', ['session_response_id'])
    op.create_index('idx_sra_behaviour_id', 'session_response_analysis', ['behaviour_id'])
    op.create_index('idx_sra_evidence_found', 'session_response_analysis', ['evidence_found'])


def downgrade() -> None:
    # Drop indexes first
    op.drop_index('idx_sra_evidence_found', table_name='session_response_analysis')
    op.drop_index('idx_sra_behaviour_id', table_name='session_response_analysis')
    op.drop_index('idx_sra_session_response_id', table_name='session_response_analysis')

    # Drop session_response_analysis table
    op.drop_table('session_response_analysis')

    # Drop indexes for checklist_item_behaviours
    op.drop_index('idx_cib_isactive', table_name='checklist_item_behaviours')
    op.drop_index('idx_cib_rowtype', table_name='checklist_item_behaviours')
    op.drop_index('idx_cib_checklistitemname', table_name='checklist_item_behaviours')

    # Drop checklist_item_behaviours table
    op.drop_table('checklist_item_behaviours')
