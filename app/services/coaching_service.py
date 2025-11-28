"""
Coaching Feedback Service
Generates personalized coaching feedback using GPT-4 and audio using ElevenLabs TTS
"""
import json
import tempfile
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
import openai
from elevenlabs import ElevenLabs
from elevenlabs.core import ApiError

from app.core.config import settings
from app.services.s3_service import get_s3_service


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

    async def generate_coaching_feedback(
        self,
        session_id: int,
        score: float,
        risk_band: str,
        strengths: List[str],
        gaps: List[str],
        category_scores: Dict[str, Any],
        customer_name: str = "",
        opportunity_name: str = ""
    ) -> Dict[str, Any]:
        """
        Generate personalized coaching feedback using GPT-4

        Args:
            session_id: Session ID for tracking
            score: Overall score (0-100)
            risk_band: Risk band (green/yellow/red)
            strengths: List of top strengths
            gaps: List of areas needing improvement
            category_scores: Detailed category breakdown
            customer_name: Customer name for context
            opportunity_name: Opportunity name for context

        Returns:
            Dict containing feedback_text, strengths, improvement_areas, action_items
        """
        try:
            print(f"Generating coaching feedback for session {session_id}")

            # Build context for GPT-4
            context = self._build_coaching_context(
                score, risk_band, strengths, gaps,
                category_scores, customer_name, opportunity_name
            )

            # Generate coaching feedback
            prompt = f"""
You are an expert B2B sales coach providing personalized feedback to a sales representative.

SALES CALL ANALYSIS:
{context}

Based on this analysis, provide coaching feedback in the following JSON format:
{{
    "feedback_text": "A 200-300 word personalized coaching summary. Be encouraging but honest. Start with what they did well, then address areas for improvement. Use 'you' to make it personal. End with an actionable next step.",
    "strengths": [
        {{"point": "Strength title", "explanation": "Why this matters and how to leverage it"}},
        {{"point": "Strength title", "explanation": "Why this matters and how to leverage it"}},
        {{"point": "Strength title", "explanation": "Why this matters and how to leverage it"}}
    ],
    "improvement_areas": [
        {{"point": "Area title", "explanation": "Why this is important and specific tips to improve"}},
        {{"point": "Area title", "explanation": "Why this is important and specific tips to improve"}},
        {{"point": "Area title", "explanation": "Why this is important and specific tips to improve"}}
    ],
    "action_items": [
        "Specific, actionable task #1 for the next call",
        "Specific, actionable task #2 for the next call",
        "Specific, actionable task #3 for the next call"
    ]
}}

Return ONLY valid JSON, no additional text.
"""

            response = self.openai_client.chat.completions.create(
                model=settings.OPENAI_MODEL_GPT,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert B2B sales coach. Provide constructive, personalized feedback that helps sales reps improve. Always respond with valid JSON."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1500
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

            print(f"Coaching feedback generated successfully for session {session_id}")

            return {
                "feedback_text": feedback.get("feedback_text", ""),
                "strengths": feedback.get("strengths", []),
                "improvement_areas": feedback.get("improvement_areas", []),
                "action_items": feedback.get("action_items", []),
                "generated_at": datetime.utcnow().isoformat()
            }

        except json.JSONDecodeError as e:
            print(f"Failed to parse GPT-4 response: {e}")
            # Return fallback feedback
            return self._generate_fallback_feedback(score, risk_band, strengths, gaps)
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

    def _build_coaching_context(
        self,
        score: float,
        risk_band: str,
        strengths: List[str],
        gaps: List[str],
        category_scores: Dict[str, Any],
        customer_name: str,
        opportunity_name: str
    ) -> str:
        """Build context string for GPT-4 prompt"""

        risk_descriptions = {
            "green": "Healthy - This is a strong opportunity",
            "yellow": "Caution - Some areas need attention",
            "red": "At Risk - Significant gaps need to be addressed"
        }

        context_parts = [
            f"Overall Score: {score:.0f}/100 ({risk_band.upper()} - {risk_descriptions.get(risk_band, 'Unknown')})",
        ]

        if customer_name:
            context_parts.append(f"Customer: {customer_name}")
        if opportunity_name:
            context_parts.append(f"Opportunity: {opportunity_name}")

        context_parts.append(f"\nTop Strengths: {', '.join(strengths) if strengths else 'None identified'}")
        context_parts.append(f"Areas for Improvement: {', '.join(gaps) if gaps else 'None identified'}")

        if category_scores:
            context_parts.append("\nCategory Breakdown:")
            for cat_id, cat_data in category_scores.items():
                if isinstance(cat_data, dict):
                    name = cat_data.get('name', f'Category {cat_id}')
                    cat_score = cat_data.get('score', 0)
                    max_score = cat_data.get('max_score', 100)
                    percentage = (cat_score / max_score * 100) if max_score > 0 else 0
                    context_parts.append(f"  - {name}: {percentage:.0f}%")

        return "\n".join(context_parts)

    def _generate_fallback_feedback(
        self,
        score: float,
        risk_band: str,
        strengths: List[str],
        gaps: List[str]
    ) -> Dict[str, Any]:
        """Generate fallback feedback if GPT-4 fails"""

        if risk_band == "green":
            tone = "Great job on this sales call!"
        elif risk_band == "yellow":
            tone = "Good effort on this call, with some areas to strengthen."
        else:
            tone = "This call has significant opportunities for improvement."

        feedback_text = f"""{tone} Your overall score was {score:.0f}/100.

Your strongest areas were: {', '.join(strengths) if strengths else 'not yet identified'}.

Focus on improving: {', '.join(gaps) if gaps else 'Continue your good work!'}.

For your next call, make sure to validate all key checklist items and gather complete information from your prospect."""

        return {
            "feedback_text": feedback_text,
            "strengths": [{"point": s, "explanation": "Identified as a strength"} for s in strengths[:3]],
            "improvement_areas": [{"point": g, "explanation": "Needs improvement"} for g in gaps[:3]],
            "action_items": [
                "Review the gaps identified and prepare questions to address them",
                "Practice the checklist items before your next call",
                "Set a goal to improve your score by 10 points"
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
