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

    def build_analysis_prompt(self, items: List[ChecklistItem], transcript: str) -> str:
        """
        Build the AI prompt for analyzing the transcript against all 10 checklist items.

        This prompt is carefully crafted to:
        1. Provide clear context about the task
        2. Define each checklist item with Definition + Key Behavior
        3. Request structured JSON output
        4. Ensure Yes/No decisions are based on demonstrated evidence
        """

        items_description = []
        for idx, item in enumerate(items, start=1):
            items_description.append(f"""
ITEM {idx}: {item.title}
Definition: {item.definition}
""")

        prompt = f"""You are an expert sales coach analyzing a sales call transcript to evaluate if a salesperson demonstrated specific behaviors and validated key information.

Your task: Evaluate the transcript against 10 checklist items. For each item, determine:
- YES (true) if the salesperson clearly demonstrated the behavior or validated the required information
- NO (false) if the behavior was not demonstrated or the information was not validated

Be objective and evidence-based. Only mark YES if there is clear evidence in the transcript.

=== CHECKLIST ITEMS ===
{''.join(items_description)}

=== TRANSCRIPT ===
{transcript}

=== INSTRUCTIONS ===
1. Read the entire transcript carefully
2. For each of the 10 items above, determine if the salesperson demonstrated that behavior
3. Provide a brief reasoning (1-2 sentences) explaining your decision
4. Return your analysis as JSON

Output format (JSON):
{{
  "items": [
    {{
      "item_number": 1,
      "answer": true,
      "reasoning": "The salesperson asked about the trigger event and confirmed measurable outcomes..."
    }},
    {{
      "item_number": 2,
      "answer": false,
      "reasoning": "There was no discussion about priority or urgency from decision influencers..."
    }},
    ... (continue for all 10 items)
  ]
}}

Analyze now and return ONLY the JSON output (no additional text):
"""
        return prompt

    async def analyze_transcript(
        self,
        transcript: str,
        db: AsyncSession
    ) -> Dict[int, Dict[str, any]]:
        """
        Analyze a transcript and return Yes/No answers for all 10 checklist items.

        Args:
            transcript: The full sales call transcript
            db: Database session

        Returns:
            Dict mapping item_id to {answer: bool, reasoning: str}
            Example: {
                114: {"answer": True, "reasoning": "Salesperson identified trigger event..."},
                115: {"answer": False, "reasoning": "Priority was not validated..."},
                ...
            }
        """

        # Get all checklist items
        items = await self.get_checklist_items(db)

        if len(items) != 10:
            raise ValueError(f"Expected 10 checklist items, found {len(items)}")

        # Build prompt
        prompt = self.build_analysis_prompt(items, transcript)

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
                    "reasoning": item_result["reasoning"]
                }

            return analysis_results

        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse AI response as JSON: {str(e)}")
        except Exception as e:
            raise RuntimeError(f"AI analysis failed: {str(e)}")

    async def analyze_and_score(
        self,
        transcript: str,
        db: AsyncSession
    ) -> tuple[Dict[int, Dict], int]:
        """
        Analyze transcript and calculate total score.

        Returns:
            (analysis_results, total_score)
            where total_score = count of YES answers * 10
        """
        results = await self.analyze_transcript(transcript, db)

        # Calculate score: each YES = 10 points
        total_score = sum(10 if item_data["answer"] else 0 for item_data in results.values())

        return results, total_score


# Singleton instance
analyzer = ChecklistAnalyzer()
