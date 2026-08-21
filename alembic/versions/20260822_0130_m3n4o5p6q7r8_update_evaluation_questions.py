"""Update evaluation questions from APP Coaching Questions 8-21-26.

Revision ID: m3n4o5p6q7r8
Revises: l2m3n4o5p6q7
Create Date: 2026-08-22 01:30:00.000000

Replaces the long per-item question lists in checklist_item_behaviours with
the six evaluation questions from the client document. Existing Question rows
are deactivated (not deleted) so historical session_response_analysis FKs remain.
"""
from typing import Dict, List, Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "m3n4o5p6q7r8"
down_revision: Union[str, None] = "l2m3n4o5p6q7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Checklist item title -> 6 evaluation questions (document order).
# Decision-Making Process Q6 was truncated in the source Word file; completed
# to match the other items' closing "Next Best Action" pattern.
EVALUATION_QUESTIONS: Dict[str, List[str]] = {
    "Customer Fit": [
        "Which specific Customer Fit criteria does this customer meet, and what evidence supports each one?",
        "What customer-verified evidence shows they have a business need we can solve successfully?",
        "What evidence shows they are willing and able to buy and that the opportunity justifies our time and resources?",
        "What evidence shows senior leaders and the necessary Decision Influencers are accessible, engaged, and taking ownership of the problem?",
        "What evidence shows the customer values our differentiation and communicates openly, honestly, and responsively?",
        "Which Fit criteria remain unverified or indicate poor Fit, and should we validate further, invest, or exit?",
    ],
    "Trigger Event & Impact (Results)": [
        "What specific, observable incident, failure, or change occurred, and what customer evidence confirms it?",
        "What exactly does the customer need to Fix, Accomplish, or Avoid?",
        "Is the identified Trigger Event the root cause or only a symptom, and what evidence proves it?",
        "What measurable financial, operational, or strategic impact does the customer expect, and how will they define success?",
        "Why must the customer act now, what happens if they do nothing, and what customer-verified timing confirms the urgency?",
        "Which parts of the Trigger Event, impact, or timing remain unverified, who will confirm them, and what is the Next Best Action?",
    ],
    "Sales Target": [
        "What exactly does the customer intend to buy?",
        "How much do they intend to purchase, including quantity, value, locations, or users?",
        "By what specific date do they intend to make the buying decision?",
        "Who confirmed what, how much, and by when, and where is that target documented or communicated?",
        "What customer evidence supports the expected decision date, and what happens if it slips?",
        "What remains unverified about what, how much, or by when, and what is the Next Best Action to confirm it?",
    ],
    "Decision Making Process": [
        "What exact steps will the customer follow from evaluation through final purchase?",
        "What step are we in now, and what is the customer's next step?",
        "Who owns each step, and what evidence confirms that responsibility?",
        "What decision criteria will the customer use to evaluate the alternatives?",
        "What approvals, purchasing requirements, and dates govern the process, and what could delay or block it?",
        "Which part of the Decision-Making Process is still assumed, who will verify it, and what is the Next Best Action?",
    ],
    "Decision Influencers (DI)": [
        "Who are the Utilizers, Specifiers, the Finalizer, and other key influencers, and what evidence confirms each person's role and level of influence?",
        "Who will use the solution, what evidence confirms each person's Utilizer role, and what requirements have they confirmed?",
        "Who defines the decision criteria or specifications, what evidence confirms each person's Specifier role, and what have they confirmed?",
        "Who has final authority to say yes or no, what evidence confirms that they are the Finalizer, and have we engaged them?",
        "Who else can influence, delay, or stop the purchase, including external advisors, and what evidence confirms their influence?",
        "Which role, level of influence, or access remains unverified, and what is the Next Best Action to close the gap?",
    ],
    "Mentor": [
        "Who is our Mentor, and what evidence shows they are a credible and influential customer insider?",
        "What non-public information have they shared that we could not have learned from outside the organization?",
        "What risks, obstacles, alternatives, or internal priorities have they helped us uncover?",
        "How have they helped us navigate the buying process, influence Decision Influencers, or access the Finalizer?",
        "What specific action have they taken recently to advance or protect our position, and would they do the same for a competitor?",
        "If Mentor status is uncertain or no Mentor exists, what does that signal, who is the strongest candidate, and what is the Next Best Action?",
    ],
    "Trigger Priority": [
        "Where does this Trigger Event rank among the customer's other priorities, and what evidence confirms that ranking?",
        "How has the Finalizer demonstrated that this initiative will receive funding, resources, attention, and action?",
        "Which Decision Influencers consider it a high priority, which do not, and what has each person confirmed?",
        "What other initiatives are competing for the same budget, resources, or leadership attention?",
        "What could delay, replace, or stop this initiative, and what evidence shows the priority is strong enough to withstand those risks?",
        "What remains unverified about Trigger Priority, how can our Mentor help, and what is the Next Best Action?",
    ],
    "Alternatives": [
        "What alternatives is the customer considering, including competitors, an internal solution, postponement, another initiative, or doing nothing?",
        "Which alternatives are actively being considered, what customer evidence confirms that, and what is the current default choice?",
        "Which Decision Influencers support each alternative, and why?",
        "From the customer's perspective, what are the strengths and weaknesses of each alternative?",
        "What happens if the customer postpones the decision, reallocates the resources, or does nothing?",
        "Which alternatives remain unverified, how can our Mentor help uncover them, and what is the Next Best Action?",
    ],
    "Our Solution Ranking": [
        "Where does our solution rank against the customer's alternatives, and which Decision Influencers have confirmed that ranking?",
        "What direct customer evidence supports our current ranking?",
        "Which decision criteria and outcomes matter most, and how does the customer rank us against each one?",
        'What evidence shows the key Decision Influencers consider our differentiators valuable and unique, and understand the "so what?" connection to their Trigger Event and business impact?',
        "Who favors another alternative, why, and what advantages or gaps do they perceive?",
        "If our ranking is unclear, stalled, declining, or not first, what must we verify or change, and what is the Next Best Action?",
    ],
    "Individual Impact": [
        "What personal outcome does each key Decision Influencer expect to gain if this initiative succeeds?",
        "What customer-verified evidence shows that each personal outcome matters to them?",
        "What is the Finalizer's WIIFM, and how have we confirmed it directly?",
        "How have we connected our solution to each influencer's personal success, recognition, security, workload, or goals?",
        "Who benefits if the initiative succeeds, and who is negatively impacted if it does not move forward?",
        "Which Individual Impact remains unverified, how can our Mentor help, and what is the Next Best Action?",
    ],
}


def upgrade() -> None:
    conn = op.get_bind()

    items = conn.execute(
        sa.text(
            "SELECT id, title FROM checklist_items WHERE is_active = true"
        )
    ).mappings().all()
    items_by_title = {row["title"]: row["id"] for row in items}

    missing = [title for title in EVALUATION_QUESTIONS if title not in items_by_title]
    if missing:
        raise RuntimeError(
            "Cannot update evaluation questions; missing checklist items: "
            + ", ".join(missing)
        )

    for title, questions in EVALUATION_QUESTIONS.items():
        item_id = items_by_title[title]

        meta = conn.execute(
            sa.text(
                """
                SELECT checklistitemname, coachingarea
                FROM checklist_item_behaviours
                WHERE checklist_item_id = :item_id
                  AND rowtype = 'Question'
                ORDER BY isactive DESC, "order" ASC
                LIMIT 1
                """
            ),
            {"item_id": item_id},
        ).mappings().first()

        if meta is None:
            behavior = conn.execute(
                sa.text(
                    """
                    SELECT checklistitemname
                    FROM checklist_item_behaviours
                    WHERE checklist_item_id = :item_id
                    LIMIT 1
                    """
                ),
                {"item_id": item_id},
            ).mappings().first()
            framework_name = behavior["checklistitemname"] if behavior else title
            coaching_area = None
        else:
            framework_name = meta["checklistitemname"]
            coaching_area = meta["coachingarea"]

        conn.execute(
            sa.text(
                """
                UPDATE checklist_item_behaviours
                SET isactive = false, updatedat = now()
                WHERE checklist_item_id = :item_id
                  AND rowtype = 'Question'
                  AND isactive = true
                """
            ),
            {"item_id": item_id},
        )

        for order, question in enumerate(questions, start=1):
            conn.execute(
                sa.text(
                    """
                    INSERT INTO checklist_item_behaviours (
                        checklistitemname,
                        rowtype,
                        coachingarea,
                        "order",
                        question,
                        behaviour,
                        keyreminder,
                        isactive,
                        createdat,
                        updatedat,
                        checklist_item_id
                    )
                    VALUES (
                        :name,
                        'Question',
                        :coachingarea,
                        :q_order,
                        :question,
                        NULL,
                        NULL,
                        true,
                        now(),
                        now(),
                        :item_id
                    )
                    """
                ),
                {
                    "name": framework_name,
                    "coachingarea": coaching_area,
                    "q_order": order,
                    "question": question,
                    "item_id": item_id,
                },
            )


def downgrade() -> None:
    conn = op.get_bind()

    items = conn.execute(
        sa.text(
            "SELECT id, title FROM checklist_items WHERE is_active = true"
        )
    ).mappings().all()
    items_by_title = {row["title"]: row["id"] for row in items}

    for title, questions in EVALUATION_QUESTIONS.items():
        item_id = items_by_title.get(title)
        if item_id is None:
            continue

        for question in questions:
            conn.execute(
                sa.text(
                    """
                    DELETE FROM checklist_item_behaviours
                    WHERE checklist_item_id = :item_id
                      AND rowtype = 'Question'
                      AND isactive = true
                      AND question = :question
                    """
                ),
                {"item_id": item_id, "question": question},
            )

        conn.execute(
            sa.text(
                """
                UPDATE checklist_item_behaviours
                SET isactive = true, updatedat = now()
                WHERE checklist_item_id = :item_id
                  AND rowtype = 'Question'
                  AND isactive = false
                """
            ),
            {"item_id": item_id},
        )
