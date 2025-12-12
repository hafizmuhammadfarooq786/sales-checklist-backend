"""
OpenAI Transcription Service
"""
import openai
from pathlib import Path
from typing import Optional, Dict, Any, Union, BinaryIO
import json

from app.core.config import settings


class TranscriptionService:
    """Service for transcribing audio files using OpenAI Whisper"""

    def __init__(self):
        if not settings.OPENAI_API_KEY:
            raise ValueError("OpenAI API key not configured")
        
        # Set OpenAI API key
        openai.api_key = settings.OPENAI_API_KEY
        self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

    async def transcribe_audio(
        self,
        file_source: Union[str, BinaryIO],
        session_id: int,
        filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Transcribe audio file using OpenAI Whisper

        Args:
            file_source: Either a file path (str) or file-like object (BytesIO)
            session_id: Session ID for tracking
            filename: Original filename (required when using BytesIO)

        Returns:
            Dict containing transcription results
        """
        try:
            # Handle file path (local files)
            if isinstance(file_source, str):
                audio_file_path = Path(file_source)
                if not audio_file_path.exists():
                    raise FileNotFoundError(f"Audio file not found: {file_source}")

                print(f"🎙️ Starting transcription for session {session_id}")
                print(f"📁 File: {audio_file_path.name} ({audio_file_path.stat().st_size} bytes)")

                # Open and transcribe the audio file
                with open(audio_file_path, "rb") as audio_file:
                    transcript = self.client.audio.transcriptions.create(
                        model=settings.OPENAI_MODEL_WHISPER,
                        file=audio_file,
                        response_format="verbose_json",
                        language="en"
                    )

            # Handle BytesIO (streaming from S3)
            else:
                if not filename:
                    raise ValueError("filename is required when using BytesIO")

                file_size = file_source.seek(0, 2)  # Seek to end to get size
                file_source.seek(0)  # Reset to beginning

                print(f"🎙️ Starting transcription for session {session_id}")
                print(f"📁 File: {filename} ({file_size} bytes) [streaming from S3]")

                # Transcribe directly from BytesIO
                # OpenAI requires a tuple (filename, file_object) for BytesIO
                transcript = self.client.audio.transcriptions.create(
                    model=settings.OPENAI_MODEL_WHISPER,
                    file=(filename, file_source),
                    response_format="verbose_json",
                    language="en"
                )

            # Extract results
            result = {
                "text": transcript.text,
                "language": getattr(transcript, 'language', 'en'),
                "duration": getattr(transcript, 'duration', None),
                "segments": getattr(transcript, 'segments', []),
                "words": getattr(transcript, 'words', []),
            }

            print(f"✅ Transcription completed successfully")
            print(f"📝 Text length: {len(result['text'])} characters")
            print(f"⏱️ Duration: {result.get('duration', 'unknown')} seconds")

            return result

        except Exception as e:
            print(f"❌ Transcription failed for session {session_id}: {str(e)}")
            raise e

    async def analyze_with_gpt4(self, transcript_text: str, session_id: int) -> Dict[str, Any]:
        """
        Analyze transcript with GPT-4 to suggest checklist responses
        """
        try:
            print(f"🤖 Starting GPT-4 analysis for session {session_id}")

            # Create analysis prompt
            prompt = f"""
You are an expert sales coach analyzing a sales call transcript. Your job is to evaluate whether specific sales criteria were met during the call.

Based on the transcript below, analyze whether these 10 key sales criteria were validated (Yes/No):

1. Trigger Event Identified: Was a specific trigger event that prompted this sales conversation identified?
2. Priority Level Confirmed: Was the priority level of this initiative for the customer confirmed?
3. Sales Goals Understood: Were the customer's sales targets and how the solution helps achieve them understood?
4. Key Influencer Engaged: Was the key decision influencer identified and engaged?
5. Personal Impact Identified: Was how success/failure impacts individuals personally understood?
6. Mentor Dynamics Mapped: Were key mentor relationships and influence patterns identified?
7. Decision Process Mapped: Was the complete decision-making process and timeline mapped out?
8. Solution Fit Validated: Was it validated that the solution is a strong fit for their needs?
9. Alternatives Discussed: Were the alternatives they're considering (competitors, status quo, etc.) understood?
10. Ranking Position Understood: Was how the solution ranks against other options understood?

For each criterion, provide:
- "validated": true/false
- "confidence": 0.0-1.0 (how confident you are in this assessment)
- "evidence": Brief quote or description from transcript supporting your assessment
- "reasoning": 1-2 sentences explaining your decision

Respond in JSON format.

TRANSCRIPT:
{transcript_text}
"""

            response = self.client.chat.completions.create(
                model=settings.OPENAI_MODEL_GPT,
                messages=[
                    {"role": "system", "content": "You are an expert sales coach and analyst."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=2000
            )

            # Parse the response
            analysis_text = response.choices[0].message.content
            
            # Try to parse as JSON, fallback to text if it fails
            try:
                analysis = json.loads(analysis_text)
            except json.JSONDecodeError:
                print(f"⚠️ Could not parse GPT-4 response as JSON")
                raise ValueError("Invalid GPT-4 response format")

            print(f"✅ GPT-4 analysis completed")
            print(f"📊 Analyzed {len(analysis.get('items', []))} criteria")

            return analysis

        except Exception as e:
            print(f"❌ GPT-4 analysis failed: {str(e)}")
            raise e


# Service instance
transcription_service = TranscriptionService()