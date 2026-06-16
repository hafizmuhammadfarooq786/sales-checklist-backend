"""update risk band thresholds to 0-30 / 40-60 / 70-100

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-06-16 12:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _reclassify_sql() -> str:
    return """
        CASE
            WHEN total_score <= 30 THEN 'RED'::riskband
            WHEN total_score >= 70 THEN 'GREEN'::riskband
            WHEN total_score >= 40 THEN 'YELLOW'::riskband
            ELSE 'RED'::riskband
        END
    """


def upgrade() -> None:
    case_sql = _reclassify_sql()
    op.execute(
        sa.text(f"UPDATE scoring_results SET risk_band = {case_sql}")
    )
    op.execute(
        sa.text(f"UPDATE score_history SET risk_band = {case_sql}")
    )


def downgrade() -> None:
    # Previous thresholds: 0-30 / 31-60 / 61-100
    op.execute(
        sa.text(
            """
            UPDATE scoring_results
            SET risk_band = CASE
                WHEN total_score <= 30 THEN 'RED'::riskband
                WHEN total_score <= 60 THEN 'YELLOW'::riskband
                ELSE 'GREEN'::riskband
            END
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE score_history
            SET risk_band = CASE
                WHEN total_score <= 30 THEN 'RED'::riskband
                WHEN total_score <= 60 THEN 'YELLOW'::riskband
                ELSE 'GREEN'::riskband
            END
            """
        )
    )
