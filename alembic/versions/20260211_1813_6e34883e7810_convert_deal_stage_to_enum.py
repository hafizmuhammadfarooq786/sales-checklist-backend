"""convert_deal_stage_to_enum

Revision ID: 6e34883e7810
Revises: db580e9cfe94
Create Date: 2026-02-11 18:13:44.143861

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6e34883e7810'
down_revision: Union[str, None] = 'db580e9cfe94'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create the enum type
    dealstage_enum = sa.Enum(
        'prospect', 'qualified', 'proposal', 'negotiation',
        'won', 'lost', 'no_decision', 'on_hold',
        name='dealstage'
    )
    dealstage_enum.create(op.get_bind(), checkfirst=True)

    # Drop the old string column and recreate as enum
    # Note: All data will be lost, but sessions table was cleared
    op.drop_column('sessions', 'deal_stage')
    op.add_column('sessions', sa.Column('deal_stage', dealstage_enum, nullable=True))


def downgrade() -> None:
    # Convert enum column back to string
    op.alter_column('sessions', 'deal_stage',
                    type_=sa.String(100),
                    postgresql_using='deal_stage::text')

    # Drop the enum type
    sa.Enum(name='dealstage').drop(op.get_bind(), checkfirst=True)
