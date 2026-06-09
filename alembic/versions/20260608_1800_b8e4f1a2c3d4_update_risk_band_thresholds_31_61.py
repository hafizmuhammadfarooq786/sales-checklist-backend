"""update risk band thresholds to 0-30 / 31-60 / 61-100

Revision ID: b8e4f1a2c3d4
Revises: a7f3c2d9e4b1
Create Date: 2026-06-08 18:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b8e4f1a2c3d4"
down_revision: Union[str, None] = "a7f3c2d9e4b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # New thresholds:
    # - RED: <= 30
    # - YELLOW: 31-60
    # - GREEN: >= 61
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


def downgrade() -> None:
    # Previous thresholds:
    # - GREEN: >= 70
    # - YELLOW: 50-69
    # - RED: < 50
    op.execute(
        sa.text(
            """
            UPDATE scoring_results
            SET risk_band = CASE
                WHEN total_score >= 70 THEN 'GREEN'::riskband
                WHEN total_score >= 50 THEN 'YELLOW'::riskband
                ELSE 'RED'::riskband
            END
            """
        )
    )

    op.execute(
        sa.text(
            """
            UPDATE score_history
            SET risk_band = CASE
                WHEN total_score >= 70 THEN 'GREEN'::riskband
                WHEN total_score >= 50 THEN 'YELLOW'::riskband
                ELSE 'RED'::riskband
            END
            """
        )
    )
