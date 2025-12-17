"""add_checklist_item_id_to_behaviours

Revision ID: 12b3e1095b59
Revises: a1b2c3d4e5f6
Create Date: 2025-12-17 13:42:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '12b3e1095b59'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: Add checklist_item_id column (nullable first)
    op.add_column('checklist_item_behaviours',
                  sa.Column('checklist_item_id', sa.Integer(), nullable=True))

    # Step 2: Populate checklist_item_id by mapping titles
    # This mapping is based on the current 10 checklist items
    # Framework title -> Checklist item title
    title_mappings = {
        "Customer Fit": "Customer Fit",
        "Trigger Event": "Trigger Event & Impact (Results)",
        "Sales Target": "Sales Target",
        "Decision Influencers — Specifier, Utilizer, Finalizer": "Decision Influencers (DI)",
        "Decision Influencer — Mentor": "Mentor",
        "Trigger Priority": "Trigger Priority",
        "Individual Impact — What's in it for Me?": "Individual Impact",
        "Finalizer": "Finalizer",
        "Alternatives": "Alternatives",
        "Our Solution Ranking": "Our Solution Ranking"
    }

    # Update each behavioural framework title to its corresponding checklist item
    for framework_title, checklist_title in title_mappings.items():
        # Escape single quotes in titles
        escaped_framework = framework_title.replace("'", "''")
        escaped_checklist = checklist_title.replace("'", "''")

        op.execute(f"""
            UPDATE checklist_item_behaviours
            SET checklist_item_id = (
                SELECT id FROM checklist_items
                WHERE title = '{escaped_checklist}'
                AND is_active = true
                LIMIT 1
            )
            WHERE checklistitemname = '{escaped_framework}'
        """)

    # Step 3: Make checklist_item_id NOT NULL
    op.alter_column('checklist_item_behaviours', 'checklist_item_id',
                    existing_type=sa.Integer(),
                    nullable=False)

    # Step 4: Add foreign key constraint
    op.create_foreign_key(
        'fk_checklist_item_behaviours_item_id',
        'checklist_item_behaviours',
        'checklist_items',
        ['checklist_item_id'],
        ['id'],
        ondelete='CASCADE'
    )

    # Step 5: Create index for better query performance
    op.create_index('idx_cib_checklist_item_id', 'checklist_item_behaviours', ['checklist_item_id'])


def downgrade() -> None:
    # Remove index
    op.drop_index('idx_cib_checklist_item_id', table_name='checklist_item_behaviours')

    # Remove foreign key
    op.drop_constraint('fk_checklist_item_behaviours_item_id', 'checklist_item_behaviours', type_='foreignkey')

    # Remove column
    op.drop_column('checklist_item_behaviours', 'checklist_item_id')
