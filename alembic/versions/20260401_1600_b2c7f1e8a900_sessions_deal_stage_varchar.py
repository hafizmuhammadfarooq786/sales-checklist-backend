"""sessions deal_stage: varchar instead of PG enum

Revision ID: b2c7f1e8a900
Revises: a1d9e4b2c801
Create Date: 2026-04-01 16:00:00.000000

PostgreSQL native ENUM `dealstage` frequently drifts from application enums
(missing labels after partial migrations, case mismatches). Storing deal_stage
as VARCHAR(32) removes that failure mode; validation stays in SQLAlchemy/Pydantic.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b2c7f1e8a900"
down_revision: Union[str, None] = "a1d9e4b2c801"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute(
        sa.text(
            "ALTER TABLE sessions "
            "ALTER COLUMN deal_stage TYPE VARCHAR(64) USING deal_stage::text"
        )
    )
    op.execute(sa.text("DROP TYPE IF EXISTS dealstage"))


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    dealstage = sa.Enum(
        "active",
        "prospect",
        "qualified",
        "proposal",
        "negotiation",
        "won",
        "lost",
        "no_decision",
        "disengaged",
        "on_hold",
        name="dealstage",
    )
    dealstage.create(bind, checkfirst=True)
    op.execute(
        sa.text(
            "ALTER TABLE sessions ALTER COLUMN deal_stage TYPE dealstage "
            "USING deal_stage::dealstage"
        )
    )
