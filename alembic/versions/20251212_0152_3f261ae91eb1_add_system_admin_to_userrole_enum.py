"""add_system_admin_to_userrole_enum

Revision ID: 3f261ae91eb1
Revises: 475e7ea9f0bc
Create Date: 2025-12-12 01:52:42.593901

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3f261ae91eb1'
down_revision: Union[str, None] = '475e7ea9f0bc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add SYSTEM_ADMIN value to the userrole enum type in PostgreSQL
    # Note: We need to check if the value already exists before adding it
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_enum
                WHERE enumlabel = 'SYSTEM_ADMIN'
                AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'userrole')
            ) THEN
                ALTER TYPE userrole ADD VALUE 'SYSTEM_ADMIN';
            END IF;
        END
        $$;
    """)


def downgrade() -> None:
    # Cannot safely remove enum value from PostgreSQL without recreating the entire type
    # and all dependent columns. Downgrade not supported for this migration.
    # If needed, manually remove the enum value or recreate the type.
    pass
