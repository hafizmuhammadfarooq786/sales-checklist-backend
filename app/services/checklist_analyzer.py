"""
AI-Powered Checklist Analyzer Service

This service analyzes sales call transcripts using OpenAI GPT-4 to automatically
evaluate all 10 checklist items based on demonstrated behaviors.

Each item is scored as:
- YES (True) = 10 points - Behavior was clearly demonstrated
- NO (False) = 0 points - Behavior was not demonstrated

The AI evaluates based on:
1. Item Definition (what must be validated)
2. Key Salesperson Behavior (what should be demonstrated)
3. Transcript content (actual call recording)
"""
import json
from typing import List, Dict
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.models.checklist import ChecklistItem, ChecklistCategory
from app.models.checklist_behaviour import ChecklistItemBehaviour, SessionResponseAnalysis


class ChecklistAnalyzer:
    """Analyzes transcripts and generates Yes/No answers for all 10 checklist items"""

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "gpt-4-turbo-preview"  # or "gpt-4" depending on availability

    async def get_checklist_items(self, db: AsyncSession) -> List[ChecklistItem]:
        """Fetch all 10 active checklist items with their categories"""
        query = (
            select(ChecklistItem)
            .join(ChecklistCategory)
            .where(ChecklistItem.is_active == True)
            .where(ChecklistCategory.is_active == True)
            .order_by(ChecklistCategory.order)
        )
        result = await db.execute(query)
        return result.scalars().all()

    async def get_behavioral_framework(
        self,
        item_id: int,
        db: AsyncSession
    ) -> Dict[str, List[ChecklistItemBehaviour]]:
        """
        Fetch behavioral framework data for a specific checklist item by ID.

        Returns dict with:
        - 'behaviors': List of behavior summary rows
        - 'questions': List of question rows (ordered)
        - 'reminders': List of key reminder rows
        """
        query = (
            select(ChecklistItemBehaviour)
            .where(ChecklistItemBehaviour.checklist_item_id == item_id)
            .where(ChecklistItemBehaviour.isactive == True)
            .order_by(ChecklistItemBehaviour.order)
        )
        result = await db.execute(query)
        all_rows = result.scalars().all()

        # Group by row type
        framework = {
            'behaviors': [r for r in all_rows if r.rowtype == 'Behavior'],
            'questions': [r for r in all_rows if r.rowtype == 'Question'],
            'reminders': [r for r in all_rows if r.rowtype == 'Reminder']
        }

        return framework

    async def build_analysis_prompt(
        self,
        items: List[ChecklistItem],
        transcript: str,
        db: AsyncSession
    ) -> tuple[str, Dict[str, Dict]]:
        """
        Build the AI prompt for analyzing the transcript against all 10 checklist items.
        Now includes behavioral framework for each item.

        Returns:
            (prompt_text, behavioral_data_map)
            where behavioral_data_map is {item_title: framework_dict}
        """

        items_description = []
        behavioral_data_map = {}

        for idx, item in enumerate(items, start=1):
            # Fetch behavioral framework for this item (by ID)
            framework = await self.get_behavioral_framework(item.id, db)
            behavioral_data_map[item.title] = framework

            # Build behavior summary
            behavior_text = ""
            if framework['behaviors']:
                behavior_text = framework['behaviors'][0].behaviour or ""

            # Build questions list
            questions_text = ""
            if framework['questions']:
                questions_list = [
                    f"  Q{q.order}: {q.question}"
                    for q in framework['questions']
                ]
                questions_text = "\n".join(questions_list)

            # Build coaching area
            coaching_area = ""
            if framework['questions']:
                coaching_area = framework['questions'][0].coachingarea or ""

            # Build key reminders
            reminder_text = ""
            if framework['reminders']:
                reminder_text = framework['reminders'][0].keyreminder or ""

            items_description.append(f"""
ITEM {idx}: {item.title}
Definition: {item.definition}

Behavior to Look For:
{behavior_text}

Coaching Area: {coaching_area}

Evaluation Questions (answer each individually):
{questions_text}

Key Reminder:
{reminder_text}
""")

        prompt = f"""You are an expert sales coach analyzing a sales call transcript to evaluate if a salesperson demonstrated specific behaviors and validated key information.

Your task: Evaluate the transcript against 10 checklist items. For each item:
1. Answer EACH evaluation question individually (Yes/No + evidence)
2. Based on all question answers, determine the overall item answer:
   - YES (true) if the salesperson clearly demonstrated the behavior
   - NO (false) if the behavior was not demonstrated

Be objective and evidence-based. Only mark YES if there is clear evidence in the transcript.

=== CHECKLIST ITEMS ===
{''.join(items_description)}

=== TRANSCRIPT ===
{transcript}

=== INSTRUCTIONS ===
1. Read the entire transcript carefully
2. For each of the 10 items above:
   a. Answer EACH evaluation question (Yes/No + quote evidence from transcript if found)
   b. Determine overall item answer based on questions
   c. Provide brief reasoning for overall decision
3. Return your analysis as JSON

Output format (JSON):
{{
  "items": [
    {{
      "item_number": 1,
      "answer": true,
      "reasoning": "Overall summary of why this item was marked Yes/No",
      "question_evaluations": [
        {{
          "question_number": 1,
          "evidence_found": true,
          "evidence_text": "Direct quote from transcript showing this was addressed",
          "reasoning": "Brief explanation"
        }},
        {{
          "question_number": 2,
          "evidence_found": false,
          "evidence_text": null,
          "reasoning": "This was not discussed in the call"
        }},
        ... (for all questions of this item)
      ]
    }},
    ... (continue for all 10 items)
  ]
}}

Analyze now and return ONLY the JSON output (no additional text):
"""
        return prompt, behavioral_data_map

    async def analyze_transcript(
        self,
        transcript: str,
        db: AsyncSession,
        session_id: int = None
    ) -> Dict[int, Dict[str, any]]:
        """
        Analyze a transcript and return Yes/No answers for all 10 checklist items.
        Now includes per-question evaluation and stores results in session_response_analysis.

        Args:
            transcript: The full sales call transcript
            db: Database session
            session_id: Optional session ID for storing question analyses

        Returns:
            Dict mapping item_id to {
                answer: bool,
                reasoning: str,
                question_evaluations: List[Dict] (per-question results)
            }
        """

        # Get all checklist items
        items = await self.get_checklist_items(db)

        if len(items) != 10:
            raise ValueError(f"Expected 10 checklist items, found {len(items)}")

        # Build prompt (now async and returns behavioral data)
        prompt, behavioral_data_map = await self.build_analysis_prompt(items, transcript, db)

        try:
            # Call OpenAI API
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert sales coach who evaluates sales calls objectively and provides structured feedback."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,  # Lower temperature for more consistent, objective responses
                response_format={"type": "json_object"}  # Ensure JSON output
            )

            # Parse response
            result_text = response.choices[0].message.content
            result_json = json.loads(result_text)

            # Map results to item IDs
            analysis_results = {}
            for idx, item in enumerate(items):
                item_result = result_json["items"][idx]
                analysis_results[item.id] = {
                    "answer": item_result["answer"],
                    "reasoning": item_result["reasoning"],
                    "question_evaluations": item_result.get("question_evaluations", []),
                    "behavioral_framework": behavioral_data_map.get(item.title, {})
                }

            return analysis_results

        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse AI response as JSON: {str(e)}")
        except Exception as e:
            raise RuntimeError(f"AI analysis failed: {str(e)}")

    async def store_question_analyses(
        self,
        session_response_id: int,
        item_id: int,
        question_evaluations: List[Dict],
        db: AsyncSession
    ):
        """
        Store per-question evaluation results in session_response_analysis table.

        Args:
            session_response_id: ID of the session_response record
            item_id: ID of the checklist item (to find behaviour records)
            question_evaluations: List of question evaluation results from AI
            db: Database session
        """
        # Fetch behavioral framework to get behaviour_ids for questions
        framework = await self.get_behavioral_framework(item_id, db)
        questions = framework['questions']

        # Map question numbers to behaviour IDs
        question_id_map = {q.order: q.id for q in questions}

        # Store each question evaluation
        for q_eval in question_evaluations:
            question_num = q_eval.get("question_number")
            behaviour_id = question_id_map.get(question_num)

            if behaviour_id:
                analysis_record = SessionResponseAnalysis(
                    session_response_id=session_response_id,
                    behaviour_id=behaviour_id,
                    evidence_found=q_eval.get("evidence_found", False),
                    evidence_text=q_eval.get("evidence_text"),
                    ai_reasoning=q_eval.get("reasoning"),
                    confidence_score=q_eval.get("confidence_score")  # Optional, if AI provides it
                )
                db.add(analysis_record)

        await db.flush()  # Flush to ensure records are saved

    async def analyze_and_score(
        self,
        transcript: str,
        db: AsyncSession,
        session_id: int = None
    ) -> tuple[Dict[int, Dict], int]:
        """
        Analyze transcript and calculate total score.

        Returns:
            (analysis_results, total_score)
            where total_score = count of YES answers * 10
        """
        results = await self.analyze_transcript(transcript, db, session_id)

        # Calculate score: each YES = 10 points
        total_score = sum(10 if item_data["answer"] else 0 for item_data in results.values())

        return results, total_score


# Singleton instance
analyzer = ChecklistAnalyzer()
