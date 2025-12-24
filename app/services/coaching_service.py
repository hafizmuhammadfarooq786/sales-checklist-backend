"""
Coaching Feedback Service
Generates personalized coaching feedback using hardcoded guidance text
Now uses gap-based coaching: focuses only on items scoring 0/10
Audio generation is disabled (code commented out but preserved)
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


# Hardcoded coaching feedback for each checklist item (client-provided)
HARDCODED_COACHING_FEEDBACK = {
    "Customer Fit": "Systematically identifies all alternatives — competitors, internal options, and \"do nothing\" — understands who supports each and uses that insight to differentiate and reduce risk.",

    "Trigger Event & Impact (Results)": "Clearly identifies why Decision Influencers want to change now, the event or condition driving urgency, and how success will be measured.",

    "Sales Target": "Understands — from the customer's perspective — what they are planning to buy, how much, why, when, and how the decision will be made.",

    "Finalizer": "Understands — from the customer's perspective — what they are buying, how much, why, when, and how the decision will be made. Verified through evidence, not assumption.",

    "Decision Influencers (DI)": "Specifiers define what gets bought. Utilizers decide if it will work. Finalizers decide whether it gets bought.",

    "Mentor": "Develops true Mentors, validates their commitment through actions, and leverages them strategically throughout the pursuit.",

    "Trigger Priority": "Recognizes that even when a company is buying (RFQ/RFP), urgency varies by Decision Influencer — and validates priority individually, not collectively.",

    "Alternatives": "Systematically identifies all alternatives — competitors, internal options, and \"do nothing\" — understands who supports each and uses that insight to differentiate and reduce risk.",

    "Our Solution Ranking": "Understands how Decision Influencers rank the solution itself, confirms whether differentiators are essential and unique, and actively shifts negative perceptions when needed.",

    "Individual Impact": "Understands that people buy, companies do not and seeks to link their product or service to what is important to each individual key Decision Influencer in a manner that the competition cannot."
}


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
        Fetch gap analysis for items scoring 0/10.
        Returns list of gap items with only: title, definition, and coaching area.

        Per client requirement: Don't judge behavior summary, questions, and key reminders.
        Only judge by: definition, coaching area, and title.
        """
        # Get all session responses for this session with score = 0
        responses_result = await db.execute(
            select(SessionResponse)
            .options(selectinload(SessionResponse.item))
            .where(SessionResponse.session_id == session_id)
            .where(SessionResponse.score == 0)  # Only items with 0/10
        )
        gap_responses = responses_result.scalars().all()

        gap_items = []

        for response in gap_responses:
            item = response.item

            # Fetch coaching area from behavioral framework (if exists)
            framework_result = await db.execute(
                select(ChecklistItemBehaviour)
                .where(ChecklistItemBehaviour.checklist_item_id == item.id)
                .where(ChecklistItemBehaviour.isactive == True)
                .where(ChecklistItemBehaviour.rowtype == 'Question')
                .order_by(ChecklistItemBehaviour.order)
                .limit(1)
            )
            framework_row = framework_result.scalar_one_or_none()
            coaching_area = framework_row.coachingarea if framework_row else ""

            gap_items.append({
                'item_title': item.title,
                'item_definition': item.definition,
                'coaching_area': coaching_area
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
        Generate gap-based coaching feedback using HARDCODED text.
        Per client requirement: Uses predefined coaching guidance for each category.
        NO AI generation - uses static coaching text defined in HARDCODED_COACHING_FEEDBACK.

        Args:
            session_id: Session ID for tracking
            score: Overall score (0-100)
            risk_band: Risk band (green/yellow/red)
            db: Database session to fetch gap data
            customer_name: Customer name for context (for display only)
            opportunity_name: Opportunity name for context (for display only)

        Returns:
            Dict containing hardcoded coaching feedback for gap items
        """
        try:
            print(f"Generating hardcoded gap-based coaching feedback for session {session_id}")

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

            # Build coaching feedback using hardcoded text for each gap
            improvement_areas = []
            feedback_parts = []

            for gap in gap_items:
                item_title = gap['item_title']

                # Get hardcoded coaching text for this item
                coaching_text = HARDCODED_COACHING_FEEDBACK.get(
                    item_title,
                    f"Review the definition and coaching area for {item_title} to improve your approach."
                )

                improvement_areas.append({
                    "point": item_title,
                    "explanation": coaching_text
                })

                feedback_parts.append(f"**{item_title}:**\n{coaching_text}\n")

            # Combine all feedback
            feedback_text = "\n".join(feedback_parts)

            # Add context header
            header = f"Coaching Feedback for {customer_name or 'this session'}"
            if opportunity_name:
                header += f" - {opportunity_name}"
            header += f"\nScore: {score:.0f}/100 | Risk Band: {risk_band.upper()}\n\n"

            feedback_text = header + feedback_text

            print(f"Hardcoded coaching feedback generated successfully for session {session_id}")

            return {
                "feedback_text": feedback_text.strip(),
                "strengths": [],  # Gap-based coaching doesn't highlight strengths
                "improvement_areas": improvement_areas,
                "action_items": ["Review the gaps above and prepare specific questions for your next call"],
                "generated_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            print(f"Error generating coaching feedback: {e}")
            raise e

    # AUDIO GENERATION DISABLED PER CLIENT REQUEST
    # The client requested to comment out audio generation functionality
    # Logic preserved for potential future use

    # async def generate_coaching_audio(
    #     self,
    #     feedback_text: str,
    #     session_id: int,
    #     user_id: int
    # ) -> Optional[Dict[str, Any]]:
    #     """
    #     Generate audio version of coaching feedback using ElevenLabs TTS
    #
    #     Args:
    #         feedback_text: Text to convert to speech
    #         session_id: Session ID for file naming
    #         user_id: User ID for S3 path
    #
    #     Returns:
    #         Dict with S3 URL and duration, or None if TTS unavailable
    #     """
    #     if not self.elevenlabs_client:
    #         print("ElevenLabs not configured, skipping audio generation")
    #         return None
    #
    #     try:
    #         print(f"Generating coaching audio for session {session_id}")
    #
    #         # Generate audio using ElevenLabs
    #         audio_generator = self.elevenlabs_client.text_to_speech.convert(
    #             voice_id=settings.ELEVENLABS_VOICE_ID,
    #             text=feedback_text,
    #             model_id="eleven_multilingual_v2",
    #             output_format="mp3_44100_128"
    #         )
    #
    #         # Collect audio bytes from generator
    #         audio_bytes = b"".join(audio_generator)
    #
    #         # Save to temporary file
    #         temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    #         temp_file.write(audio_bytes)
    #         temp_file.close()
    #
    #         # Calculate approximate duration (128kbps = 16KB/s)
    #         duration_seconds = len(audio_bytes) / (128 * 1024 / 8)
    #
    #         # Upload to S3
    #         s3_key = f"coaching/{user_id}/{session_id}/feedback_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.mp3"
    #
    #         try:
    #             s3_service = get_s3_service()
    #             s3_url = s3_service.upload_file(
    #                 temp_file.name,
    #                 s3_key,
    #                 content_type="audio/mpeg",
    #                 bucket_name=settings.S3_BUCKET_AUDIO
    #             )
    #             storage_type = "s3"
    #         except Exception as s3_error:
    #             print(f"S3 upload failed, using local storage: {s3_error}")
    #             # Fall back to local storage
    #             local_dir = f"uploads/coaching/{user_id}/{session_id}"
    #             os.makedirs(local_dir, exist_ok=True)
    #             local_path = f"{local_dir}/feedback_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.mp3"
    #
    #             import shutil
    #             shutil.copy(temp_file.name, local_path)
    #             s3_url = local_path
    #             storage_type = "local"
    #         finally:
    #             # Clean up temp file
    #             os.unlink(temp_file.name)
    #
    #         print(f"Coaching audio generated: {s3_url} ({int(duration_seconds)}s)")
    #
    #         return {
    #             "audio_url": s3_url,
    #             "s3_bucket": settings.S3_BUCKET_AUDIO if storage_type == "s3" else None,
    #             "s3_key": s3_key if storage_type == "s3" else None,
    #             "duration_seconds": int(duration_seconds),
    #             "storage_type": storage_type
    #         }
    #
    #     except ApiError as e:
    #         print(f"ElevenLabs API error: {e}")
    #         return None
    #     except Exception as e:
    #         print(f"Error generating coaching audio: {e}")
    #         return None

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
