"""remove_key_behavior_field

Revision ID: d1b48e28ecc4
Revises: 4959a8b63fc9
Create Date: 2025-12-04 11:38:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd1b48e28ecc4'
down_revision = '0c704dd026d0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Remove key_behavior column from checklist_items table.
    This field was never populated and has no data source.
    """
    op.drop_column('checklist_items', 'key_behavior')


def downgrade() -> None:
    """
    Re-add key_behavior column if needed (will be NULL for all rows).
    """
    op.add_column(
        'checklist_items',
        sa.Column('key_behavior', sa.Text(), nullable=True)
    )
