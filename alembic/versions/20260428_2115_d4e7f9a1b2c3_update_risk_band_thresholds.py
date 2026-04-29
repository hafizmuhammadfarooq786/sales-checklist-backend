"""update risk band thresholds to 70/50

Revision ID: d4e7f9a1b2c3
Revises: b2c7f1e8a900
Create Date: 2026-04-28 21:15:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4e7f9a1b2c3"
down_revision: Union[str, None] = "b2c7f1e8a900"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # New thresholds:
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


def downgrade() -> None:
    # Previous thresholds:
    # - GREEN: >= 70
    # - YELLOW: 40-69
    # - RED: < 40
    op.execute(
        sa.text(
            """
            UPDATE scoring_results
            SET risk_band = CASE
                WHEN total_score >= 70 THEN 'GREEN'::riskband
                WHEN total_score >= 40 THEN 'YELLOW'::riskband
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
                WHEN total_score >= 40 THEN 'YELLOW'::riskband
                ELSE 'RED'::riskband
            END
            """
        )
    )
