"""rename_finalizer_to_decision_making_process

Revision ID: 2f1ebf5f8086
Revises: 0be34dd10c1f
Create Date: 2026-03-13 21:28:16.595871

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2f1ebf5f8086'
down_revision: Union[str, None] = '0be34dd10c1f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: Rename checklist item from "Finalizer" to "Decision Making Process"
    op.execute("""
        UPDATE checklist_items
        SET title = 'Decision Making Process'
        WHERE title = 'Finalizer'
        AND is_active = true
    """)

    # Step 2: Update existing scoring results - top_strengths JSON array
    op.execute("""
        UPDATE scoring_results
        SET top_strengths = replace(top_strengths::text, '"Finalizer"', '"Decision Making Process"')::json
        WHERE top_strengths::text LIKE '%"Finalizer"%'
    """)

    # Step 3: Update existing scoring results - top_gaps JSON array
    op.execute("""
        UPDATE scoring_results
        SET top_gaps = replace(top_gaps::text, '"Finalizer"', '"Decision Making Process"')::json
        WHERE top_gaps::text LIKE '%"Finalizer"%'
    """)

    # Step 4: Update category_scores JSON in scoring_results
    # Use simple string replace on the JSON text
    op.execute("""
        UPDATE scoring_results
        SET category_scores = replace(category_scores::text, '"Finalizer"', '"Decision Making Process"')::json
        WHERE category_scores::text LIKE '%"Finalizer"%'
    """)

    # Step 5: Update existing coaching_feedback - feedback_text
    op.execute("""
        UPDATE coaching_feedback
        SET feedback_text = replace(feedback_text, 'Finalizer', 'Decision Making Process')
        WHERE feedback_text LIKE '%Finalizer%'
    """)

    # Step 6: Update existing coaching_feedback - improvement_areas JSON
    op.execute("""
        UPDATE coaching_feedback
        SET improvement_areas = replace(improvement_areas::text, '"Finalizer"', '"Decision Making Process"')::json
        WHERE improvement_areas::text LIKE '%"Finalizer"%'
    """)

    # Step 7: Update existing coaching_feedback - strengths JSON
    op.execute("""
        UPDATE coaching_feedback
        SET strengths = replace(strengths::text, '"Finalizer"', '"Decision Making Process"')::json
        WHERE strengths::text LIKE '%"Finalizer"%'
    """)


def downgrade() -> None:
    # Revert Step 7: Restore coaching_feedback strengths
    op.execute("""
        UPDATE coaching_feedback
        SET strengths = replace(strengths::text, '"Decision Making Process"', '"Finalizer"')::json
        WHERE strengths::text LIKE '%"Decision Making Process"%'
    """)

    # Revert Step 6: Restore coaching_feedback improvement_areas
    op.execute("""
        UPDATE coaching_feedback
        SET improvement_areas = replace(improvement_areas::text, '"Decision Making Process"', '"Finalizer"')::json
        WHERE improvement_areas::text LIKE '%"Decision Making Process"%'
    """)

    # Revert Step 5: Restore coaching_feedback feedback_text
    op.execute("""
        UPDATE coaching_feedback
        SET feedback_text = replace(feedback_text, 'Decision Making Process', 'Finalizer')
        WHERE feedback_text LIKE '%Decision Making Process%'
    """)

    # Revert Step 4: Restore category_scores JSON
    op.execute("""
        UPDATE scoring_results
        SET category_scores = replace(category_scores::text, '"Decision Making Process"', '"Finalizer"')::json
        WHERE category_scores::text LIKE '%"Decision Making Process"%'
    """)

    # Revert Step 3: Restore top_gaps JSON array
    op.execute("""
        UPDATE scoring_results
        SET top_gaps = replace(top_gaps::text, '"Decision Making Process"', '"Finalizer"')::json
        WHERE top_gaps::text LIKE '%"Decision Making Process"%'
    """)

    # Revert Step 2: Restore top_strengths JSON array
    op.execute("""
        UPDATE scoring_results
        SET top_strengths = replace(top_strengths::text, '"Decision Making Process"', '"Finalizer"')::json
        WHERE top_strengths::text LIKE '%"Decision Making Process"%'
    """)

    # Revert Step 1: Restore checklist item title
    op.execute("""
        UPDATE checklist_items
        SET title = 'Finalizer'
        WHERE title = 'Decision Making Process'
        AND is_active = true
    """)
