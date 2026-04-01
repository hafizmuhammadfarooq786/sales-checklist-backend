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
import re
from typing import List, Dict, Optional
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
        # Use gpt-4o or gpt-4-turbo (latest models with better JSON mode support)
        self.model = "gpt-4o"  # Faster and cheaper than gpt-4-turbo-preview

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

    async def get_behavioral_frameworks_bulk(
        self,
        item_ids: List[int],
        db: AsyncSession,
    ) -> Dict[int, Dict[str, List[ChecklistItemBehaviour]]]:
        """One query for all items; avoids N+1 when building the analysis prompt."""
        if not item_ids:
            return {}
        by_item: Dict[int, Dict[str, List[ChecklistItemBehaviour]]] = {
            iid: {
                "behaviors": [],
                "questions": [],
                "reminders": [],
            }
            for iid in item_ids
        }
        query = (
            select(ChecklistItemBehaviour)
            .where(ChecklistItemBehaviour.checklist_item_id.in_(item_ids))
            .where(ChecklistItemBehaviour.isactive == True)
            .order_by(
                ChecklistItemBehaviour.checklist_item_id,
                ChecklistItemBehaviour.order,
            )
        )
        result = await db.execute(query)
        for row in result.scalars().all():
            bucket = by_item.get(row.checklist_item_id)
            if bucket is None:
                continue
            if row.rowtype == "Behavior":
                bucket["behaviors"].append(row)
            elif row.rowtype == "Question":
                bucket["questions"].append(row)
            elif row.rowtype == "Reminder":
                bucket["reminders"].append(row)
        return by_item

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
        bulk = await self.get_behavioral_frameworks_bulk([item_id], db)
        return bulk.get(item_id, {"behaviors": [], "questions": [], "reminders": []})

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
        item_ids = [item.id for item in items]
        frameworks_by_item_id = await self.get_behavioral_frameworks_bulk(item_ids, db)

        for idx, item in enumerate(items, start=1):
            framework = frameworks_by_item_id.get(
                item.id, {"behaviors": [], "questions": [], "reminders": []}
            )
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

IMPORTANT JSON FORMATTING RULES:
- Keep evidence_text quotes SHORT (max 50 words) and reasoning BRIEF (1 sentence)
- Escape all quotes in strings using \\\" (backslash-double-quote)
- Escape all newlines in strings using \\n (backslash-n)
- Do NOT include unescaped quotes or newlines in any string values
- Keep all string values on a single line when possible

=== CHECKLIST ITEMS ===
{''.join(items_description)}

=== TRANSCRIPT ===
{transcript[:8000]}

=== INSTRUCTIONS ===
1. Read the transcript carefully
2. For each of the 10 items above:
   a. Answer EACH evaluation question (Yes/No + SHORT quote if found)
   b. Determine overall item answer based on questions
   c. Provide BRIEF reasoning (1-2 sentences max)
3. Return your analysis as JSON

Output format (JSON):
{{
  "items": [
    {{
      "item_number": 1,
      "answer": true,
      "reasoning": "Brief summary why Yes/No (max 2 sentences)",
      "question_evaluations": [
        {{
          "question_number": 1,
          "evidence_found": true,
          "evidence_text": "Short quote (max 50 words)",
          "reasoning": "Brief explanation (1 sentence)"
        }},
        {{
          "question_number": 2,
          "evidence_found": false,
          "evidence_text": null,
          "reasoning": "Not discussed"
        }}
      ]
    }}
  ]
}}

CRITICAL REQUIREMENTS:
- You MUST return exactly 10 items (item_number 1 through 10)
- Each item MUST have item_number matching its position (1, 2, 3, ..., 10)
- Do NOT skip any items, even if the transcript doesn't contain relevant information
- For items with no evidence, set answer: false and provide reasoning explaining why

Return ONLY valid JSON, no additional text:
"""
        return prompt, behavioral_data_map

    def extract_json_from_text(self, text: str) -> Optional[str]:
        """
        Extract JSON from text, handling various formats:
        - Plain JSON
        - JSON in markdown code blocks (```json ... ```)
        - JSON with trailing text
        - Malformed JSON with common issues
        """
        # First, try to find JSON in markdown code blocks
        json_block_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
        match = re.search(json_block_pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()

        # Try to find JSON object starting with {
        json_start = text.find('{')
        if json_start != -1:
            # Find the matching closing brace
            brace_count = 0
            in_string = False
            escape_next = False
            
            for i in range(json_start, len(text)):
                char = text[i]
                
                if escape_next:
                    escape_next = False
                    continue
                
                if char == '\\':
                    escape_next = True
                    continue
                
                if char == '"' and not escape_next:
                    in_string = not in_string
                    continue
                
                if not in_string:
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            return text[json_start:i+1]
        
        return None

    def fix_common_json_issues(self, json_str: str) -> str:
        """
        Attempt to fix common JSON issues:
        - Unescaped quotes in strings
        - Unescaped newlines in strings
        - Trailing commas
        """
        # This is a simplified fix - for production, consider using a more robust approach
        # or asking the AI to regenerate the response
        
        # Remove trailing commas before } or ]
        json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
        
        # Try to fix unescaped newlines in string values (basic approach)
        # This is tricky because we need to identify string boundaries
        # For now, we'll rely on the AI to generate proper JSON with response_format
        
        return json_str

    def parse_json_response(self, response_text: str, session_id: Optional[int] = None) -> Dict:
        """
        Parse JSON from AI response with robust error handling and recovery.
        
        Returns:
            Parsed JSON dictionary
            
        Raises:
            ValueError: If JSON cannot be parsed after all recovery attempts
        """
        import os
        
        # Step 1: Extract JSON from text
        cleaned_text = self.extract_json_from_text(response_text)
        if not cleaned_text:
            cleaned_text = response_text.strip()
        
        # Step 2: Remove markdown code blocks if still present
        if cleaned_text.startswith("```"):
            lines = cleaned_text.split("\n")
            lines = lines[1:]  # Remove first line
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned_text = "\n".join(lines).strip()
        
        # Step 3: Try to parse JSON
        try:
            return json.loads(cleaned_text)
        except json.JSONDecodeError as e:
            # Step 4: Try to fix common issues
            try:
                fixed_text = self.fix_common_json_issues(cleaned_text)
                return json.loads(fixed_text)
            except json.JSONDecodeError:
                pass
            
            # Step 5: Log error details
            print(f"❌ JSON Parse Error: {str(e)}")
            error_pos = getattr(e, 'pos', 0)
            start = max(0, error_pos - 200)
            end = min(len(cleaned_text), error_pos + 200)
            print(f"Problematic text around error position:")
            print(f"...{cleaned_text[start:end]}...")
            
            # Step 6: Save full response for debugging
            debug_dir = "/tmp/ai_debug"
            os.makedirs(debug_dir, exist_ok=True)
            debug_file = f"{debug_dir}/failed_response_{session_id}.txt"
            with open(debug_file, "w", encoding="utf-8") as f:
                f.write(response_text)
            print(f"💾 Full response saved to: {debug_file}")
            
            # Step 7: Try to extract partial JSON (find the largest valid JSON object)
            # This is a last resort - try to find a valid JSON structure
            try:
                # Try to find the items array and parse it
                items_match = re.search(r'"items"\s*:\s*\[(.*?)\]', cleaned_text, re.DOTALL)
                if items_match:
                    # Try to reconstruct a minimal valid JSON
                    # This is a fallback - not ideal but might work
                    pass
            except Exception:
                pass
            
            raise ValueError(f"Failed to parse AI response as JSON: {str(e)}. Response saved to {debug_file}")

    async def analyze_transcript(
        self,
        transcript: str,
        db: AsyncSession,
        session_id: int = None,
        retry_count: int = 0,
        max_retries: int = 1
    ) -> Dict[int, Dict[str, any]]:
        """
        Analyze a transcript and return Yes/No answers for all 10 checklist items.
        Now includes per-question evaluation and stores results in session_response_analysis.

        Args:
            transcript: The full sales call transcript
            db: Database session
            session_id: Optional session ID for storing question analyses
            retry_count: Internal parameter for retry logic
            max_retries: Maximum number of retries if JSON parsing fails

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
                        "content": "You are an expert sales coach who evaluates sales calls objectively and provides structured feedback. Return ONLY valid JSON with no additional text. Ensure all string values are properly escaped (use \\\" for quotes, \\n for newlines)."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,  # Lower temperature for more consistent, objective responses
                max_tokens=8000,  # Large enough for 10 items with detailed question evaluations (~700 tokens/item)
                response_format={"type": "json_object"}  # Ensure JSON output
            )

            # Parse response
            result_text = response.choices[0].message.content

            # Log the response for debugging
            print(f"=== RAW AI RESPONSE (first 1000 chars) ===")
            print(result_text[:1000])
            print(f"=== END RAW RESPONSE (total length: {len(result_text)}) ===")

            # Use robust JSON parsing with error recovery
            try:
                result_json = self.parse_json_response(result_text, session_id)
            except ValueError as parse_error:
                # If parsing fails and we haven't exceeded retries, ask AI to fix the JSON
                if retry_count < max_retries:
                    print(f"⚠️ JSON parsing failed, attempting retry {retry_count + 1}/{max_retries}...")
                    # Use full response but truncate if too long (keep last 10000 chars if needed)
                    response_to_fix = result_text if len(result_text) <= 10000 else result_text[-10000:]
                    fix_prompt = f"""The previous JSON response had parsing errors. Please fix the following JSON to ensure it's valid:

{response_to_fix}

CRITICAL REQUIREMENTS:
- Return ONLY the corrected, valid JSON with no additional text
- Escape all quotes in strings using \\\" (backslash-double-quote)
- Escape all newlines in strings using \\n (backslash-n)
- Ensure all string values are properly escaped
- Keep evidence_text and reasoning fields short and on single lines when possible
- MUST include exactly 10 items (item_number 1 through 10)
- Each item MUST have item_number matching its position (1, 2, 3, ..., 10)
- Do NOT skip any items"""
                    
                    fix_response = await self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {
                                "role": "system",
                                "content": "You are a JSON repair assistant. Fix the provided JSON to make it valid. Return ONLY valid JSON with no additional text."
                            },
                            {
                                "role": "user",
                                "content": fix_prompt
                            }
                        ],
                        temperature=0.1,
                        max_tokens=4000,
                        response_format={"type": "json_object"}
                    )
                    
                    fixed_text = fix_response.choices[0].message.content
                    print(f"=== FIXED AI RESPONSE (first 1000 chars) ===")
                    print(fixed_text[:1000])
                    print(f"=== END FIXED RESPONSE (total length: {len(fixed_text)}) ===")
                    
                    # Try to parse the fixed response
                    try:
                        result_json = self.parse_json_response(fixed_text, session_id)
                    except ValueError as fix_error:
                        # Even the fixed version failed, raise the original error
                        raise parse_error
                else:
                    # Max retries exceeded, raise the original error
                    raise parse_error

            # Validate response structure
            if "items" not in result_json:
                raise ValueError("AI response missing 'items' array")
            
            items_response = result_json["items"]
            if not isinstance(items_response, list):
                raise ValueError(f"AI response 'items' is not a list, got {type(items_response)}")
            
            if len(items_response) != 10:
                raise ValueError(f"Expected 10 items in response, got {len(items_response)}. Response may be incomplete.")
            
            # Create a map of item_number to item_result for easier lookup
            items_by_number = {}
            for item_result in items_response:
                item_num = item_result.get("item_number")
                if item_num is None:
                    raise ValueError("AI response item missing 'item_number' field")
                items_by_number[item_num] = item_result
            
            # Map results to item IDs by matching item_number (1-indexed) with items list index
            analysis_results = {}
            for idx, item in enumerate(items, start=1):
                if idx not in items_by_number:
                    raise ValueError(f"AI response missing item_number {idx} (expected for item: {item.title})")
                
                item_result = items_by_number[idx]
                analysis_results[item.id] = {
                    "answer": item_result.get("answer", False),
                    "reasoning": item_result.get("reasoning", "No reasoning provided"),
                    "question_evaluations": item_result.get("question_evaluations", []),
                    "behavioral_framework": behavioral_data_map.get(item.title, {})
                }

            return analysis_results

        except ValueError as e:
            # Re-raise ValueError from parse_json_response
            raise RuntimeError(f"AI analysis failed: {str(e)}")
        except Exception as e:
            raise RuntimeError(f"AI analysis failed: {str(e)}")

    async def store_question_analyses(
        self,
        session_response_id: int,
        item_id: int,
        question_evaluations: List[Dict],
        db: AsyncSession,
        framework: Optional[Dict[str, List[ChecklistItemBehaviour]]] = None,
    ):
        """
        Store per-question evaluation results in session_response_analysis table.

        Args:
            session_response_id: ID of the session_response record
            item_id: ID of the checklist item (to find behaviour records)
            question_evaluations: List of question evaluation results from AI
            db: Database session
            framework: If provided, skips re-fetching behavioural rows for this item.
        """
        if framework is None:
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
