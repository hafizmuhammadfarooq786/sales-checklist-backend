"""add organization management tables

Revision ID: 20251224_1200
Revises: 7f8a9b0c1d2e
Create Date: 2025-12-24 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20251224_1200'
down_revision: Union[str, None] = '7f8a9b0c1d2e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create invitations table
    op.create_table(
        'invitations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('team_id', sa.Integer(), nullable=True),
        sa.Column('role', sa.String(length=50), nullable=False),
        sa.Column('token', sa.String(length=255), nullable=False),
        sa.Column('invited_by', sa.Integer(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('accepted_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()'), onupdate=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['invited_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token')
    )

    # Create indexes for invitations
    op.create_index('idx_invitations_email', 'invitations', ['email'])
    op.create_index('idx_invitations_token', 'invitations', ['token'])
    op.create_index('idx_invitations_organization_id', 'invitations', ['organization_id'])

    # Create organization_settings table
    op.create_table(
        'organization_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('allow_self_registration', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('default_role', sa.String(length=50), nullable=False, server_default='rep'),
        sa.Column('logo_url', sa.Text(), nullable=True),
        sa.Column('primary_color', sa.String(length=7), nullable=True),
        sa.Column('settings', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()'), onupdate=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id')
    )

    # Create index for organization_settings
    op.create_index('idx_organization_settings_organization_id', 'organization_settings', ['organization_id'])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index('idx_organization_settings_organization_id', table_name='organization_settings')
    op.drop_table('organization_settings')

    op.drop_index('idx_invitations_organization_id', table_name='invitations')
    op.drop_index('idx_invitations_token', table_name='invitations')
    op.drop_index('idx_invitations_email', table_name='invitations')
    op.drop_table('invitations')
