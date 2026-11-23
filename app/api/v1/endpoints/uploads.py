"""
Audio file upload endpoints
"""
import logging
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, BackgroundTasks
from fastapi.concurrency import run_in_threadpool
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

        # Validate session mode (audio upload only for audio mode sessions)
        from app.models.session import SessionMode

        if session.session_mode != SessionMode.AUDIO:
            logger.warning(f"Audio upload attempted for manual mode session {session_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "INVALID_SESSION_MODE",
                    "message": "Audio upload is only available for audio mode sessions. This session is in manual mode.",
                    "session_mode": session.session_mode.value,
                    "suggestion": f"Use POST /api/v1/sessions/{session_id}/manual-checklist to submit the checklist"
                }
            )

        logger.info(f"Session {session_id} found and validated (audio mode), proceeding with upload")

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

            # Upload to S3 on ECS/staging (task IAM role) or when static AWS keys are set
            if settings.s3_audio_bucket:
                try:
                    s3_service = get_s3_service()
                    s3_url = await run_in_threadpool(
                        s3_service.upload_file,
                        temp_file_path,
                        s3_key,
                        audio_file.content_type,
                    )
                    storage_type = "s3"
                    file_path = s3_url  # Store S3 URL as file_path
                    logger.info(f"File uploaded to S3: {s3_url}")
                except Exception:
                    # Fall back to local storage if S3 fails
                    logger.warning(f"S3 upload failed for session {session_id}, falling back to local storage", exc_info=True)
                    local_dir = Path("uploads")
                    local_dir.mkdir(exist_ok=True)
                    local_path = local_dir / unique_filename
                    await run_in_threadpool(shutil.copy, temp_file_path, str(local_path))
                    storage_type = "local"
                    file_path = str(local_path)
                    logger.info(f"File saved to local storage: {file_path}")
            else:
                # Local storage (development mode)
                local_dir = Path("uploads")
                local_dir.mkdir(exist_ok=True)
                local_path = local_dir / unique_filename
                await run_in_threadpool(shutil.copy, temp_file_path, str(local_path))
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

        from app.services.transcription_dispatcher import schedule_transcription

        queue = schedule_transcription(session_id, file_path, background_tasks)
        logger.info(
            "Transcription scheduled for session %s (%s)", session_id, queue
        )

        return {
            "id": audio_file_record.id,
            "session_id": session_id,
            "filename": unique_filename,
            "file_size": file_size,
            "mime_type": audio_file.content_type,
            "storage_type": storage_type,
            "file_path": file_path if storage_type == "s3" else None,
            "status": "analyzing",
            "queue": queue,
            "message": "Audio uploaded successfully. Transcription and analysis started in background.",
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
        "storage_type": audio_file.storage_type,
        "created_at": audio_file.created_at,
    }


# ---------------------------------------------------------------------------
# Direct upload to S3 (staging on Lambda)
#
# A Lambda request cannot carry more than 6 MB, and audio can be 25 MB. With
# DIRECT_UPLOADS_ENABLED the browser asks for a signed form, sends the file
# straight to S3, then tells the API it is there. The API never sees the bytes.
#
# With the setting off, which is the default and what production uses, both
# routes answer 404 and the upload above is the only path.
# ---------------------------------------------------------------------------

DIRECT_UPLOAD_AUDIO_TYPES = (
    "audio/webm",
    "audio/wav",
    "audio/mp3",
    "audio/mpeg",
    "audio/mp4",
    "audio/m4a",
    "audio/ogg",
    "audio/x-m4a",
    "audio/x-wav",
)
DIRECT_UPLOAD_EXPIRES_SECONDS = 600


class DirectUploadRequest(BaseModel):
    filename: str
    content_type: str
    file_size: int


class DirectUploadComplete(BaseModel):
    key: str


def require_direct_uploads() -> None:
    if not settings.DIRECT_UPLOADS_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "DIRECT_UPLOADS_DISABLED"},
        )


def key_is_directly_under(key: str, prefix: str) -> bool:
    """
    True only for a file sitting directly in the folder `prefix`: nothing
    nested, no traversal. The browser sends the key back at the second step,
    so it cannot be trusted as it arrives.
    """
    if not key.startswith(prefix):
        return False
    name = key[len(prefix):]
    return bool(name) and "/" not in name and ".." not in name


def audio_key_prefix(user_id: int, session_id: int) -> str:
    return f"audio/{user_id}/{session_id}/"


def owns_audio_key(key: str, user_id: int, session_id: int) -> bool:
    """A key this user could have been given for this session, and no other."""
    return key_is_directly_under(key, audio_key_prefix(user_id, session_id))


def _too_large(file_size: int) -> HTTPException:
    file_size_mb = file_size / 1024 / 1024
    return HTTPException(
        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        detail={
            "error": "FILE_TOO_LARGE",
            "message": f"File size ({file_size_mb:.2f} MB) exceeds maximum allowed size ({settings.MAX_AUDIO_FILE_SIZE_MB} MB). Please compress the audio file or use a shorter recording.",
            "max_size_mb": settings.MAX_AUDIO_FILE_SIZE_MB,
            "file_size_mb": round(file_size_mb, 2),
        },
    )


async def _audio_session_for_upload(db: AsyncSession, session_id: int, user_id: int) -> Session:
    from app.models.session import SessionMode

    result = await db.execute(
        select(Session).where(Session.id == session_id, Session.user_id == user_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if session.session_mode != SessionMode.AUDIO:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "INVALID_SESSION_MODE",
                "message": "Audio upload is only available for audio mode sessions. This session is in manual mode.",
                "session_mode": session.session_mode.value,
            },
        )
    return session


@router.post("/{session_id}/upload-url")
async def create_audio_upload_url(
    session_id: int,
    body: DirectUploadRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Step 1 of a direct upload: a signed form for one audio file."""
    require_direct_uploads()

    if body.content_type not in DIRECT_UPLOAD_AUDIO_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail={
                "error": "INVALID_FILE_TYPE",
                "message": f"File type '{body.content_type}' is not supported. Please upload an audio file.",
                "supported_types": list(DIRECT_UPLOAD_AUDIO_TYPES),
            },
        )
    max_bytes = settings.MAX_AUDIO_FILE_SIZE_MB * 1024 * 1024
    if body.file_size <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")
    if body.file_size > max_bytes:
        raise _too_large(body.file_size)

    await _audio_session_for_upload(db, session_id, user_id)

    existing = await db.execute(select(AudioFile).where(AudioFile.session_id == session_id))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "AUDIO_ALREADY_EXISTS"},
        )

    extension = Path(body.filename or "recording.webm").suffix
    key = f"{audio_key_prefix(user_id, session_id)}{session_id}_{uuid.uuid4().hex}{extension}"
    form = await run_in_threadpool(
        get_s3_service().generate_presigned_upload,
        key,
        body.content_type,
        max_bytes,
        DIRECT_UPLOAD_EXPIRES_SECONDS,
    )
    return {
        "url": form["url"],
        "fields": form["fields"],
        "key": key,
        "expires_in": DIRECT_UPLOAD_EXPIRES_SECONDS,
    }


@router.post("/{session_id}/upload-complete", status_code=status.HTTP_201_CREATED)
async def complete_audio_upload(
    session_id: int,
    body: DirectUploadComplete,
    background_tasks: BackgroundTasks,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Step 2 of a direct upload: record the file and start transcription."""
    require_direct_uploads()

    if not owns_audio_key(body.key, user_id, session_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "INVALID_UPLOAD_KEY"},
        )

    session = await _audio_session_for_upload(db, session_id, user_id)

    # Called twice (a retry, a double click): answer as the first call did.
    # Nothing is recorded or started a second time.
    existing_result = await db.execute(select(AudioFile).where(AudioFile.session_id == session_id))
    existing = existing_result.scalar_one_or_none()
    if existing:
        return {
            "id": existing.id,
            "session_id": session_id,
            "filename": existing.filename,
            "file_size": existing.file_size,
            "mime_type": existing.mime_type,
            "storage_type": existing.storage_type,
            "file_path": existing.file_path if existing.storage_type == "s3" else None,
            "message": "Audio file already exists for this session.",
        }

    s3_service = get_s3_service()
    info = await run_in_threadpool(s3_service.object_info, body.key)
    if not info:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "UPLOAD_NOT_FOUND", "message": "The file has not arrived in storage."},
        )
    # S3 already enforced the size through the signed form; this is the
    # second lock on the same door.
    if info["size"] > settings.MAX_AUDIO_FILE_SIZE_MB * 1024 * 1024:
        raise _too_large(info["size"])

    file_path = s3_service.object_url(body.key)
    filename = body.key.rsplit("/", 1)[-1]
    mime_type = info.get("content_type") or "application/octet-stream"
    audio_file_record = AudioFile(
        session_id=session_id,
        filename=filename,
        file_path=file_path,
        file_size=info["size"],
        mime_type=mime_type,
        storage_type="s3",
    )
    db.add(audio_file_record)
    session.status = SessionStatus.ANALYZING
    await db.commit()
    await db.refresh(audio_file_record)

    from app.services.transcription_dispatcher import schedule_transcription

    queue = schedule_transcription(session_id, file_path, background_tasks)
    logger.info("Direct upload recorded for session %s; transcription scheduled (%s)", session_id, queue)

    return {
        "id": audio_file_record.id,
        "session_id": session_id,
        "filename": filename,
        "file_size": info["size"],
        "mime_type": mime_type,
        "storage_type": "s3",
        "file_path": file_path,
        "status": "analyzing",
        "queue": queue,
        "message": "Audio uploaded successfully. Transcription and analysis started in background.",
    }
