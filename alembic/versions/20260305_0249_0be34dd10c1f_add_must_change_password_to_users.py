"""add_must_change_password_to_users

Revision ID: 0be34dd10c1f
Revises: 654ba0ebc01f
Create Date: 2026-03-05 02:49:36.443379

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0be34dd10c1f'
down_revision: Union[str, None] = '654ba0ebc01f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add must_change_password column to users table
    op.add_column('users', sa.Column('must_change_password', sa.Boolean(), nullable=False, server_default='false'))

    # Remove server default after adding column
    op.alter_column('users', 'must_change_password', server_default=None)


def downgrade() -> None:
    # Drop must_change_password column
    op.drop_column('users', 'must_change_password')
