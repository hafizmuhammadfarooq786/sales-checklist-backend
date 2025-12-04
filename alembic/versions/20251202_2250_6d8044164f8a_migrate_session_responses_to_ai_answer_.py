"""migrate_session_responses_to_ai_answer_schema

Revision ID: 6d8044164f8a
Revises: e91fc140a02a
Create Date: 2025-12-02 22:50:35.922765

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6d8044164f8a'
down_revision: Union[str, None] = 'e91fc140a02a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Migrate session_responses table from old validation schema to new AI answer schema.

    Old schema: is_validated, confidence, evidence_text, manual_override, etc.
    New schema: ai_answer, user_answer, was_changed, changed_at, score
    """
    # Drop old columns that are no longer needed
    op.drop_column('session_responses', 'override_reason')
    op.drop_column('session_responses', 'override_by_user_id')
    op.drop_column('session_responses', 'manual_override')
    op.drop_column('session_responses', 'evidence_text')
    op.drop_column('session_responses', 'confidence')
    op.drop_column('session_responses', 'is_validated')

    # Add new columns for AI answer system
    op.add_column('session_responses', sa.Column('ai_answer', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.add_column('session_responses', sa.Column('user_answer', sa.Boolean(), nullable=True))
    op.add_column('session_responses', sa.Column('was_changed', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.add_column('session_responses', sa.Column('changed_at', sa.DateTime(), nullable=True))
    op.add_column('session_responses', sa.Column('score', sa.Integer(), nullable=False, server_default=sa.text('0')))

    # Remove server defaults after creation (they were only for existing rows)
    op.alter_column('session_responses', 'ai_answer', server_default=None)
    op.alter_column('session_responses', 'was_changed', server_default=None)
    op.alter_column('session_responses', 'score', server_default=None)


def downgrade() -> None:
    """
    Rollback to old validation schema (NOT RECOMMENDED - data loss will occur)
    """
    # Remove new columns
    op.drop_column('session_responses', 'score')
    op.drop_column('session_responses', 'changed_at')
    op.drop_column('session_responses', 'was_changed')
    op.drop_column('session_responses', 'user_answer')
    op.drop_column('session_responses', 'ai_answer')

    # Restore old columns
    op.add_column('session_responses', sa.Column('is_validated', sa.Boolean(), nullable=True))
    op.add_column('session_responses', sa.Column('confidence', sa.Double(), nullable=True))
    op.add_column('session_responses', sa.Column('evidence_text', sa.Text(), nullable=True))
    op.add_column('session_responses', sa.Column('manual_override', sa.Boolean(), nullable=True))
    op.add_column('session_responses', sa.Column('override_by_user_id', sa.Integer(), nullable=True))
    op.add_column('session_responses', sa.Column('override_reason', sa.Text(), nullable=True))
