"""add_audio_support_to_manager_notes

Revision ID: db580e9cfe94
Revises: 7ec002909a00
Create Date: 2026-02-05 17:39:41.413306

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'db580e9cfe94'
down_revision: Union[str, None] = '7ec002909a00'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add note_type column with default 'text'
    op.add_column('manager_notes', sa.Column('note_type', sa.String(length=10), nullable=False, server_default='text'))
    op.create_index(op.f('ix_manager_notes_note_type'), 'manager_notes', ['note_type'], unique=False)

    # Make note_text nullable (required for text, null for audio)
    op.alter_column('manager_notes', 'note_text',
               existing_type=sa.TEXT(),
               nullable=True)

    # Add audio fields
    op.add_column('manager_notes', sa.Column('audio_s3_bucket', sa.String(length=255), nullable=True))
    op.add_column('manager_notes', sa.Column('audio_s3_key', sa.String(length=512), nullable=True))
    op.add_column('manager_notes', sa.Column('audio_duration', sa.Integer(), nullable=True))
    op.add_column('manager_notes', sa.Column('audio_file_size', sa.Integer(), nullable=True))


def downgrade() -> None:
    # Remove audio fields
    op.drop_column('manager_notes', 'audio_file_size')
    op.drop_column('manager_notes', 'audio_duration')
    op.drop_column('manager_notes', 'audio_s3_key')
    op.drop_column('manager_notes', 'audio_s3_bucket')

    # Make note_text not nullable again
    op.alter_column('manager_notes', 'note_text',
               existing_type=sa.TEXT(),
               nullable=False)

    # Remove note_type column
    op.drop_index(op.f('ix_manager_notes_note_type'), table_name='manager_notes')
    op.drop_column('manager_notes', 'note_type')
