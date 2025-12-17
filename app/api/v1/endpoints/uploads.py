"""
Audio file upload endpoints
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import shutil
from pathlib import Path
import uuid
import tempfile
import os

from app.db.session import get_db
from app.models.session import Session, AudioFile, SessionStatus
from app.core.config import settings
from app.services.s3_service import get_s3_service
from app.api.dependencies import get_current_user_id

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/{session_id}/upload", status_code=status.HTTP_201_CREATED)
async def upload_audio_file(
    session_id: int,
    audio_file: UploadFile,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload audio file for a session and automatically start processing

    - Validates file type
    - Saves file to S3 or local storage
    - Creates AudioFile record
    - Updates session status to "analyzing"
    - Automatically triggers background transcription and checklist generation
    """
    try:
        logger.info(f"Upload request received for session {session_id} by user {user_id}")
        logger.info(f"File: {audio_file.filename}, Content-Type: {audio_file.content_type}")
        
        # Validate file type
        valid_audio_types = [
            "audio/webm",
            "audio/wav",
            "audio/mp3",
            "audio/mpeg",
            "audio/mp4",
            "audio/m4a",
            "audio/ogg",
            "audio/x-m4a",
            "audio/x-wav"
        ]

        if not audio_file.content_type or audio_file.content_type not in valid_audio_types:
            logger.warning(f"Invalid file type: {audio_file.content_type}")
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail={
                    "error": "INVALID_FILE_TYPE",
                    "message": f"File type '{audio_file.content_type}' is not supported. Please upload an audio file.",
                    "supported_types": valid_audio_types
                }
            )

        # Get session
        result = await db.execute(
            select(Session).where(
                Session.id == session_id,
                Session.user_id == user_id,
            )
        )
        session = result.scalar_one_or_none()

        if not session:
            logger.warning(f"Session {session_id} not found for user {user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found",
            )
        
        logger.info(f"Session {session_id} found, proceeding with upload")

        # Check if audio file already exists
        existing_audio_result = await db.execute(
            select(AudioFile).where(AudioFile.session_id == session_id)
        )
        existing_audio = existing_audio_result.scalar_one_or_none()
        
        if existing_audio:
            # Return existing audio file info
            logger.info(f"Audio file already exists for session {session_id}")

            # Check if transcription has been done
            from app.models.session import Transcript
            transcript_result = await db.execute(
                select(Transcript).where(Transcript.session_id == session_id)
            )
            transcript = transcript_result.scalar_one_or_none()

            # Note: Audio exists but transcription should be triggered via separate endpoint if needed
            if not transcript:
                logger.info(f"Audio exists but no transcript found for session {session_id}. Use POST /api/v1/sessions/{session_id}/transcribe to start transcription.")

            return {
                "id": existing_audio.id,
                "session_id": session_id,
                "filename": existing_audio.filename,
                "file_size": existing_audio.file_size,
                "mime_type": existing_audio.mime_type,
                "storage_type": existing_audio.storage_type,
                "file_path": existing_audio.file_path if existing_audio.storage_type == "s3" else None,
                "message": "Audio file already exists for this session. Processing continues automatically." if not transcript else "Audio file and transcript already exist for this session.",
            }

        # Generate unique filename
        file_extension = Path(audio_file.filename or "recording.webm").suffix
        unique_filename = f"{session_id}_{uuid.uuid4().hex}{file_extension}"

        # Generate S3 key (path in bucket)
        s3_key = f"audio/{user_id}/{session_id}/{unique_filename}"

        # Initialize variables outside try block for proper scoping
        temp_file_path = None
        s3_url = None
        file_path = None
        storage_type = None
        file_size = None

        try:
            # Save to temporary file first
            logger.info(f"Creating temporary file with extension: {file_extension}")
            
            # Read file content (UploadFile is a stream, read it once)
            content = await audio_file.read()
            if not content:
                raise ValueError("Uploaded file is empty")

            logger.info(f"Read {len(content)} bytes from uploaded file")

            # Validate file size (OpenAI Whisper limit: 25 MB)
            max_size_bytes = settings.MAX_AUDIO_FILE_SIZE_MB * 1024 * 1024
            if len(content) > max_size_bytes:
                file_size_mb = len(content) / 1024 / 1024
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail={
                        "error": "FILE_TOO_LARGE",
                        "message": f"File size ({file_size_mb:.2f} MB) exceeds maximum allowed size ({settings.MAX_AUDIO_FILE_SIZE_MB} MB). Please compress the audio file or use a shorter recording.",
                        "max_size_mb": settings.MAX_AUDIO_FILE_SIZE_MB,
                        "file_size_mb": round(file_size_mb, 2)
                    }
                )
            
            # Write to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
                temp_file.write(content)
                temp_file_path = temp_file.name
                logger.info(f"Temporary file created: {temp_file_path}")

            # Get file size
            file_size = os.path.getsize(temp_file_path)
            logger.info(f"File size: {file_size} bytes")

            # Upload to S3 if enabled, otherwise use local storage
            if settings.AWS_S3_BUCKET_NAME and settings.AWS_ACCESS_KEY_ID:
                try:
                    s3_service = get_s3_service()
                    s3_url = s3_service.upload_file(
                        temp_file_path,
                        s3_key,
                        content_type=audio_file.content_type,
                    )
                    storage_type = "s3"
                    file_path = s3_url  # Store S3 URL as file_path
                    logger.info(f"File uploaded to S3: {s3_url}")
                except Exception as e:
                    # Fall back to local storage if S3 fails
                    logger.warning(f"S3 upload failed for session {session_id}, falling back to local storage", exc_info=True)
                    local_dir = Path("uploads")
                    local_dir.mkdir(exist_ok=True)
                    local_path = local_dir / unique_filename
                    shutil.copy(temp_file_path, local_path)
                    storage_type = "local"
                    file_path = str(local_path)
                    logger.info(f"File saved to local storage: {file_path}")
            else:
                # Local storage (development mode)
                local_dir = Path("uploads")
                local_dir.mkdir(exist_ok=True)
                local_path = local_dir / unique_filename
                shutil.copy(temp_file_path, local_path)
                storage_type = "local"
                file_path = str(local_path)
                logger.info(f"File saved to local storage: {file_path}")

        except HTTPException:
            # Re-raise HTTP exceptions as-is
            raise
        except Exception as e:
            error_msg = f"Error uploading audio file for session {session_id}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save file: {str(e)}",
            )
        finally:
            # Clean up temporary file
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                except Exception as e:
                    logger.warning(f"Failed to delete temporary file {temp_file_path}: {str(e)}")

        # Verify required variables are set
        if not file_path or not storage_type or file_size is None:
            logger.error(f"Critical variables not set after upload: file_path={file_path}, storage_type={storage_type}, file_size={file_size}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="File upload completed but required variables are missing",
            )

        # Create AudioFile record
        try:
            logger.info(f"Creating AudioFile record for session {session_id}")
            logger.info(f"File details: path={file_path}, size={file_size}, storage={storage_type}")
            
            audio_file_record = AudioFile(
                session_id=session_id,
                filename=unique_filename,
                file_path=file_path,  # S3 URL or local path
                file_size=file_size,
                mime_type=audio_file.content_type,
                storage_type=storage_type,
            )

            db.add(audio_file_record)

            # Update session status to ANALYZING (transcription will begin)
            session.status = SessionStatus.ANALYZING

            await db.commit()
            await db.refresh(audio_file_record)
            logger.info(f"AudioFile record created with ID: {audio_file_record.id}")
        except Exception as e:
            logger.error(f"Database error while creating AudioFile record: {str(e)}", exc_info=True)
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save file record to database: {str(e)}",
            )

        logger.info(f"Audio file uploaded successfully for session {session_id}: {unique_filename}")
        logger.info(f"Session {session_id} status updated to ANALYZING")

        # Synchronously transcribe and analyze (user waits for results)
        logger.info(f"Starting synchronous transcription and AI analysis for session {session_id}")

        try:
            from app.services.transcription_service import transcription_service
            from app.services.checklist_analyzer import analyzer
            from app.models.session import Transcript, SessionResponse
            from app.models.checklist import ChecklistItem
            from sqlalchemy import delete
            import boto3
            from io import BytesIO

            # Step 1: Transcribe audio
            logger.info(f"📝 Transcribing audio file...")

            # Handle S3 vs local storage
            if storage_type == "s3":
                # Stream file from S3 to BytesIO for transcription
                logger.info(f"Streaming audio from S3 for transcription...")
                s3_client = boto3.client(
                    "s3",
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                    region_name=settings.AWS_REGION,
                )

                file_buffer = BytesIO()
                s3_client.download_fileobj(settings.AWS_S3_BUCKET_NAME, s3_key, file_buffer)
                file_buffer.seek(0)

                # Transcribe from BytesIO
                transcript_data = await transcription_service.transcribe_audio(
                    file_buffer,
                    session_id,
                    filename=unique_filename
                )
            else:
                # Local file, transcribe directly
                transcript_data = await transcription_service.transcribe_audio(file_path, session_id)

            # Step 2: Save transcript
            transcript = Transcript(
                session_id=session_id,
                text=transcript_data["text"],
                language=transcript_data.get("language", "en"),
                duration=transcript_data.get("duration"),
                words_count=len(transcript_data["text"].split()),
                processing_time=30.0  # Placeholder
            )
            db.add(transcript)
            await db.commit()
            await db.refresh(transcript)
            logger.info(f"✅ Transcript saved ({len(transcript_data['text'])} characters)")

            # Step 3: AI analysis with behavioral framework
            logger.info(f"🤖 Analyzing transcript with behavioral framework...")
            analysis_results = await analyzer.analyze_transcript(transcript_data["text"], db, session_id)
            logger.info(f"✅ AI analysis completed for {len(analysis_results)} items")

            # Step 4: Delete old responses if they exist
            await db.execute(
                delete(SessionResponse).where(SessionResponse.session_id == session_id)
            )
            await db.commit()

            # Step 5: Create SessionResponse records with per-question evaluations
            for item_id, result in analysis_results.items():
                ai_answer = result["answer"]
                score = 10 if ai_answer else 0

                response = SessionResponse(
                    session_id=session_id,
                    item_id=item_id,
                    ai_answer=ai_answer,
                    ai_reasoning=result["reasoning"],
                    user_answer=None,
                    was_changed=False,
                    score=score,
                )
                db.add(response)
                await db.flush()

                # Store per-question evaluations
                question_evals = result.get("question_evaluations", [])
                if question_evals:
                    await analyzer.store_question_analyses(
                        session_response_id=response.id,
                        item_id=item_id,
                        question_evaluations=question_evals,
                        db=db
                    )

            # Step 6: Update session status
            session.status = "pending_review"
            await db.commit()

            logger.info(f"✅ Transcription and AI analysis completed successfully")
            logger.info(f"📊 Session {session_id} ready for review")

            return {
                "id": audio_file_record.id,
                "session_id": session_id,
                "filename": unique_filename,
                "file_size": file_size,
                "mime_type": audio_file.content_type,
                "storage_type": storage_type,
                "file_path": file_path if storage_type == "s3" else None,
                "transcript": {
                    "text": transcript_data["text"],
                    "word_count": len(transcript_data["text"].split()),
                    "duration": transcript_data.get("duration")
                },
                "analysis": {
                    "total_items": len(analysis_results),
                    "items_validated": sum(1 for r in analysis_results.values() if r["answer"]),
                },
                "message": f"Audio uploaded, transcribed, and analyzed successfully! Checklist ready for review.",
            }

        except Exception as transcription_error:
            logger.error(f"Transcription/Analysis failed for session {session_id}: {str(transcription_error)}", exc_info=True)

            # Update session to failed status
            session.status = "failed"
            await db.commit()

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Audio uploaded but transcription failed: {str(transcription_error)}",
            )
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Unexpected error in upload_audio_file: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )


@router.get("/{session_id}/audio")
async def get_audio_file_info(
    session_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Get audio file information for a session
    """
    # Verify session belongs to user
    session_result = await db.execute(
        select(Session).where(
            Session.id == session_id,
            Session.user_id == user_id,
        )
    )
    session = session_result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    # Get audio file
    audio_result = await db.execute(
        select(AudioFile).where(AudioFile.session_id == session_id)
    )
    audio_file = audio_result.scalar_one_or_none()

    if not audio_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audio file not found for this session",
        )

    return {
        "id": audio_file.id,
        "session_id": session_id,
        "filename": audio_file.filename,
        "file_size": audio_file.file_size,
        "mime_type": audio_file.mime_type,
        "duration_seconds": audio_file.duration_seconds,
        "storage_type": audio_file.storage_type,
        "created_at": audio_file.created_at,
    }
