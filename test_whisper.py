"""
Test script for OpenAI Whisper transcription
"""
import asyncio
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

async def test_whisper():
    """Test OpenAI Whisper transcription"""
    from app.services.transcription_service import transcription_service

    audio_file = "test_files/test_audio.wav"

    if not os.path.exists(audio_file):
        print(f"Error: Audio file not found: {audio_file}")
        return False

    print(f"Testing OpenAI Whisper with: {audio_file}")
    print(f"File size: {os.path.getsize(audio_file)} bytes")

    try:
        result = await transcription_service.transcribe_audio(audio_file, session_id=999)
        print("\n=== WHISPER TRANSCRIPTION RESULT ===")
        print(f"Text: {result.get('text', 'N/A')}")
        print(f"Language: {result.get('language', 'N/A')}")
        print(f"Duration: {result.get('duration', 'N/A')} seconds")
        print("=== WHISPER TEST PASSED ===")
        return True
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_whisper())
    print(f"\nWhisper Test: {'PASSED' if result else 'FAILED'}")
    sys.exit(0 if result else 1)
