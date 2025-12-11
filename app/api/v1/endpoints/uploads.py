"""
Audio file upload endpoints
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, BackgroundTasks
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
    background_tasks: BackgroundTasks,
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
        if not audio_file.content_type or not audio_file.content_type.startswith("audio/"):
            logger.warning(f"Invalid file type: {audio_file.content_type}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file type. Must be an audio file.",
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

            # Check if transcription has been done, if not, trigger it
            from app.models.session import Transcript
            transcript_result = await db.execute(
                select(Transcript).where(Transcript.session_id == session_id)
            )
            transcript = transcript_result.scalar_one_or_none()

            # Trigger transcription if it hasn't been done yet
            if not transcript:
                from app.api.v1.endpoints.transcription import process_transcription
                background_tasks.add_task(process_transcription, session_id, existing_audio.file_path)
                logger.info(f"Audio exists but no transcript found. Background transcription task queued for session {session_id}")
                session.status = SessionStatus.ANALYZING
                await db.commit()

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

        # Automatically trigger transcription and checklist generation in background
        from app.api.v1.endpoints.transcription import process_transcription
        background_tasks.add_task(process_transcription, session_id, file_path)
        logger.info(f"Background transcription task queued for session {session_id}")

        return {
            "id": audio_file_record.id,
            "session_id": session_id,
            "filename": unique_filename,
            "file_size": file_size,
            "mime_type": audio_file.content_type,
            "storage_type": storage_type,
            "file_path": file_path if storage_type == "s3" else None,  # Only expose S3 URLs
            "message": f"Audio file uploaded successfully to {storage_type}. Transcription and AI analysis started automatically in background.",
        }
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
