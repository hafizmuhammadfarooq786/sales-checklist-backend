"""Remove coaching audio (ElevenLabs TTS) columns

Removes the audio coaching columns from coaching_feedback. Audio coaching
(ElevenLabs TTS) is not part of the product and has been removed entirely.

Revision ID: a7f3c2d9e4b1
Revises: d4e7f9a1b2c3
Create Date: 2026-06-08 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a7f3c2d9e4b1'
down_revision: Union[str, None] = 'd4e7f9a1b2c3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column('coaching_feedback', 'audio_s3_bucket')
    op.drop_column('coaching_feedback', 'audio_s3_key')
    op.drop_column('coaching_feedback', 'audio_duration')


def downgrade() -> None:
    op.add_column('coaching_feedback', sa.Column('audio_duration', sa.Integer(), nullable=True))
    op.add_column('coaching_feedback', sa.Column('audio_s3_key', sa.String(length=500), nullable=True))
    op.add_column('coaching_feedback', sa.Column('audio_s3_bucket', sa.String(length=255), nullable=True))
