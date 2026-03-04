"""add_soft_delete_to_users

Revision ID: 654ba0ebc01f
Revises: c12cbbe7659d
Create Date: 2026-03-05 01:48:59.690561

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '654ba0ebc01f'
down_revision: Union[str, None] = 'c12cbbe7659d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add soft delete columns to users table
    op.add_column('users', sa.Column('deleted_at', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('deleted_by', sa.Integer(), nullable=True))

    # Create index on deleted_at for efficient queries
    op.create_index('ix_users_deleted_at', 'users', ['deleted_at'])

    # Add foreign key constraint for deleted_by
    op.create_foreign_key(
        'fk_users_deleted_by',
        'users', 'users',
        ['deleted_by'], ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    # Drop foreign key constraint
    op.drop_constraint('fk_users_deleted_by', 'users', type_='foreignkey')

    # Drop index
    op.drop_index('ix_users_deleted_at', 'users')

    # Drop columns
    op.drop_column('users', 'deleted_by')
    op.drop_column('users', 'deleted_at')
