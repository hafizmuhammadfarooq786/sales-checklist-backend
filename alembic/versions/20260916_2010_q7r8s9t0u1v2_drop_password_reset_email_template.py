"""Remove unused password_reset email template

Revision ID: q7r8s9t0u1v2
Revises: p6q7r8s9t0u1
Create Date: 2026-09-16 20:10:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "q7r8s9t0u1v2"
down_revision: Union[str, None] = "p6q7r8s9t0u1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DELETE FROM email_templates WHERE slug = 'password_reset'")


def downgrade() -> None:
    # Password-reset emails were removed; Super Admin can restore from code defaults
    # only if the template is reintroduced.
    pass
