"""
Coaching Feedback Service
Generates personalized coaching feedback using GPT-4 and audio using ElevenLabs TTS
Now uses gap-based coaching: focuses only on items scoring 0/10
"""
import json
import tempfile
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
import openai
from elevenlabs import ElevenLabs
from elevenlabs.core import ApiError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.services.s3_service import get_s3_service
from app.models.session import SessionResponse
from app.models.checklist import ChecklistItem
from app.models.checklist_behaviour import ChecklistItemBehaviour, SessionResponseAnalysis


class CoachingService:
    """Service for generating AI-powered coaching feedback"""

    def __init__(self):
        """Initialize OpenAI and ElevenLabs clients"""
        if not settings.OPENAI_API_KEY:
            raise ValueError("OpenAI API key not configured")

        self.openai_client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

        # Initialize ElevenLabs if configured
        self.elevenlabs_client = None
        if settings.ELEVENLABS_API_KEY and settings.ELEVENLABS_VOICE_ID:
            try:
                self.elevenlabs_client = ElevenLabs(api_key=settings.ELEVENLABS_API_KEY)
                print(f"ElevenLabs client initialized with voice: {settings.ELEVENLABS_VOICE_ID}")
            except Exception as e:
                print(f"Warning: ElevenLabs initialization failed: {e}")

    async def fetch_gap_data(
        self,
        session_id: int,
        db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """
        Fetch detailed gap analysis for items scoring 0/10.
        Returns list of gap items with behavioral framework and per-question evaluation.

        Each gap includes:
        - Item title, definition
        - Behavior summary
        - Questions that weren't answered (with evidence status)
        - Coaching area
        - Key reminders
        """
        # Get all session responses for this session
        responses_result = await db.execute(
            select(SessionResponse)
            .options(selectinload(SessionResponse.item))
            .options(selectinload(SessionResponse.question_analyses))
            .where(SessionResponse.session_id == session_id)
            .where(SessionResponse.score == 0)  # Only items with 0/10
        )
        gap_responses = responses_result.scalars().all()

        gap_items = []

        for response in gap_responses:
            item = response.item

            # Fetch behavioral framework for this item (by ID)
            framework_result = await db.execute(
                select(ChecklistItemBehaviour)
                .where(ChecklistItemBehaviour.checklist_item_id == item.id)
                .where(ChecklistItemBehaviour.isactive == True)
                .order_by(ChecklistItemBehaviour.order)
            )
            framework_rows = framework_result.scalars().all()

            # Group by row type
            behavior_summary = next((r.behaviour for r in framework_rows if r.rowtype == 'Behavior'), "")
            questions = [r for r in framework_rows if r.rowtype == 'Question']
            key_reminder = next((r.keyreminder for r in framework_rows if r.rowtype == 'Reminder'), "")
            coaching_area = questions[0].coachingarea if questions else ""

            # Map question analyses
            question_analyses_map = {qa.behaviour_id: qa for qa in response.question_analyses}

            # Build question list with evidence status
            question_details = []
            for q in questions:
                qa = question_analyses_map.get(q.id)
                question_details.append({
                    'order': q.order,
                    'question': q.question,
                    'evidence_found': qa.evidence_found if qa else False,
                    'evidence_text': qa.evidence_text if qa else None,
                    'reasoning': qa.ai_reasoning if qa else None
                })

            gap_items.append({
                'item_title': item.title,
                'item_definition': item.definition,
                'behavior_summary': behavior_summary,
                'coaching_area': coaching_area,
                'key_reminder': key_reminder,
                'questions': question_details,
                'ai_reasoning': response.ai_reasoning
            })

        return gap_items

    async def generate_coaching_feedback(
        self,
        session_id: int,
        score: float,
        risk_band: str,
        db: AsyncSession,
        customer_name: str = "",
        opportunity_name: str = "",
        **kwargs  # For backward compatibility with old parameters
    ) -> Dict[str, Any]:
        """
        Generate gap-based coaching feedback using GPT-4.
        Now focuses ONLY on items scoring 0/10 (skips items with 10/10).

        Args:
            session_id: Session ID for tracking
            score: Overall score (0-100)
            risk_band: Risk band (green/yellow/red)
            db: Database session to fetch gap data
            customer_name: Customer name for context
            opportunity_name: Opportunity name for context

        Returns:
            Dict containing coaching_paragraphs (gap-based coaching by item)
        """
        try:
            print(f"Generating gap-based coaching feedback for session {session_id}")

            # Fetch gap data (items with 0/10 score)
            gap_items = await self.fetch_gap_data(session_id, db)

            if not gap_items:
                # Perfect score! No gaps to coach on
                return {
                    "feedback_text": f"Excellent work! You achieved a perfect score of {score:.0f}/100 on this call. All checklist items were successfully completed. Keep up the great work and continue applying these best practices in your future calls.",
                    "strengths": [],
                    "improvement_areas": [],
                    "action_items": ["Continue applying these successful techniques in future calls"],
                    "generated_at": datetime.utcnow().isoformat()
                }

            # Build gap-based coaching prompt
            gap_descriptions = []
            for idx, gap in enumerate(gap_items, start=1):
                questions_not_answered = [
                    f"   - {q['question']}" + (f" (Evidence: {q['evidence_text'][:80]}...)" if q.get('evidence_text') else "")
                    for q in gap['questions']
                    if not q['evidence_found']
                ]

                gap_descriptions.append(f"""
GAP {idx}: {gap['item_title']}
Definition: {gap['item_definition']}
Coaching Area: {gap['coaching_area']}

What You're Missing:
{chr(10).join(questions_not_answered) if questions_not_answered else "   - All specific questions for this behavior"}

Expected Behavior:
{gap['behavior_summary']}

Key Reminder:
{gap['key_reminder']}

Why This Matters:
{gap['ai_reasoning']}
""")

            prompt = f"""You are an expert B2B sales coach providing gap-based coaching to help a sales representative achieve a 100/100 score.

CALL CONTEXT:
- Customer: {customer_name or 'N/A'}
- Opportunity: {opportunity_name or 'N/A'}
- Current Score: {score:.0f}/100
- Risk Band: {risk_band.upper()}

The salesperson has GAPS in the following checklist items (scored 0/10). Your job is to provide actionable coaching for EACH gap to help them achieve 100/100.

=== GAPS TO ADDRESS ===
{''.join(gap_descriptions)}

=== YOUR TASK ===
For each gap above, write a coaching paragraph that:
1. Explains what was missing from the call (specific questions/behaviors not demonstrated)
2. Explains why this gap matters (impact on deal success)
3. Provides specific, actionable guidance on how to address this gap in future calls
4. Includes relevant reminders and best practices

Use a supportive, coaching tone. Be specific and actionable.

Return your coaching in the following JSON format:
{{
    "gap_coaching": [
        {{
            "item_title": "Customer Fit",
            "coaching_paragraph": "A focused paragraph (100-150 words) explaining what was missing, why it matters, and how to improve. Use 'you' to make it personal. Be specific about the questions that need to be asked and behaviors that need to be demonstrated."
        }},
        ... (one entry for each gap)
    ],
    "summary": "A brief 2-3 sentence overall summary highlighting the most critical gaps to address",
    "next_call_focus": "The single most important area to focus on for the next call"
}}

Return ONLY valid JSON, no additional text.
"""

            response = self.openai_client.chat.completions.create(
                model=settings.OPENAI_MODEL_GPT,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert B2B sales coach. Provide gap-based, actionable coaching that helps sales reps achieve 100/100. Always respond with valid JSON."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2500
            )

            # Parse response
            response_text = response.choices[0].message.content.strip()

            # Clean up response if it has markdown code blocks
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
                response_text = response_text.strip()

            feedback = json.loads(response_text)

            print(f"Gap-based coaching feedback generated successfully for session {session_id}")

            # Format for backward compatibility with existing schema
            improvement_areas = [
                {
                    "point": item['item_title'],
                    "explanation": item['coaching_paragraph']
                }
                for item in feedback.get('gap_coaching', [])
            ]

            feedback_text = f"{feedback.get('summary', '')}\n\n"
            for item in feedback.get('gap_coaching', []):
                feedback_text += f"**{item['item_title']}:**\n{item['coaching_paragraph']}\n\n"

            feedback_text += f"**Next Call Focus:** {feedback.get('next_call_focus', '')}"

            return {
                "feedback_text": feedback_text.strip(),
                "strengths": [],  # Gap-based coaching doesn't highlight strengths
                "improvement_areas": improvement_areas,
                "action_items": [feedback.get('next_call_focus', 'Review gap areas and prepare questions')],
                "generated_at": datetime.utcnow().isoformat()
            }

        except json.JSONDecodeError as e:
            print(f"Failed to parse GPT-4 response: {e}")
            # Return fallback feedback
            return self._generate_gap_fallback_feedback(score, len(gap_items) if 'gap_items' in locals() else 0)
        except Exception as e:
            print(f"Error generating coaching feedback: {e}")
            raise e

    async def generate_coaching_audio(
        self,
        feedback_text: str,
        session_id: int,
        user_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Generate audio version of coaching feedback using ElevenLabs TTS

        Args:
            feedback_text: Text to convert to speech
            session_id: Session ID for file naming
            user_id: User ID for S3 path

        Returns:
            Dict with S3 URL and duration, or None if TTS unavailable
        """
        if not self.elevenlabs_client:
            print("ElevenLabs not configured, skipping audio generation")
            return None

        try:
            print(f"Generating coaching audio for session {session_id}")

            # Generate audio using ElevenLabs
            audio_generator = self.elevenlabs_client.text_to_speech.convert(
                voice_id=settings.ELEVENLABS_VOICE_ID,
                text=feedback_text,
                model_id="eleven_multilingual_v2",
                output_format="mp3_44100_128"
            )

            # Collect audio bytes from generator
            audio_bytes = b"".join(audio_generator)

            # Save to temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
            temp_file.write(audio_bytes)
            temp_file.close()

            # Calculate approximate duration (128kbps = 16KB/s)
            duration_seconds = len(audio_bytes) / (128 * 1024 / 8)

            # Upload to S3
            s3_key = f"coaching/{user_id}/{session_id}/feedback_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.mp3"

            try:
                s3_service = get_s3_service()
                s3_url = s3_service.upload_file(
                    temp_file.name,
                    s3_key,
                    content_type="audio/mpeg",
                    bucket_name=settings.S3_BUCKET_AUDIO
                )
                storage_type = "s3"
            except Exception as s3_error:
                print(f"S3 upload failed, using local storage: {s3_error}")
                # Fall back to local storage
                local_dir = f"uploads/coaching/{user_id}/{session_id}"
                os.makedirs(local_dir, exist_ok=True)
                local_path = f"{local_dir}/feedback_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.mp3"

                import shutil
                shutil.copy(temp_file.name, local_path)
                s3_url = local_path
                storage_type = "local"
            finally:
                # Clean up temp file
                os.unlink(temp_file.name)

            print(f"Coaching audio generated: {s3_url} ({int(duration_seconds)}s)")

            return {
                "audio_url": s3_url,
                "s3_bucket": settings.S3_BUCKET_AUDIO if storage_type == "s3" else None,
                "s3_key": s3_key if storage_type == "s3" else None,
                "duration_seconds": int(duration_seconds),
                "storage_type": storage_type
            }

        except ApiError as e:
            print(f"ElevenLabs API error: {e}")
            return None
        except Exception as e:
            print(f"Error generating coaching audio: {e}")
            return None

    def _generate_gap_fallback_feedback(
        self,
        score: float,
        gap_count: int
    ) -> Dict[str, Any]:
        """Generate fallback feedback if GPT-4 fails"""

        feedback_text = f"""Your overall score was {score:.0f}/100, with {gap_count} checklist items that need improvement.

To achieve a 100/100 score, focus on addressing the gaps in your sales approach. Review each checklist item that scored 0/10 and ensure you're asking the right questions and demonstrating the expected behaviors.

For your next call, prepare specific questions for each gap area and practice the behaviors needed to validate all checklist items."""

        return {
            "feedback_text": feedback_text,
            "strengths": [],
            "improvement_areas": [{"point": f"Gap Area {i+1}", "explanation": "Review and address this checklist item"} for i in range(min(gap_count, 3))],
            "action_items": [
                "Review all gap areas and prepare targeted questions",
                "Practice the expected behaviors before your next call",
                f"Set a goal to reduce gaps from {gap_count} to {max(0, gap_count-2)}"
            ],
            "generated_at": datetime.utcnow().isoformat()
        }


# Global service instance (lazy initialization)
_coaching_service: Optional[CoachingService] = None


def get_coaching_service() -> CoachingService:
    """Get or create the coaching service singleton"""
    global _coaching_service
    if _coaching_service is None:
        _coaching_service = CoachingService()
    return _coaching_service
