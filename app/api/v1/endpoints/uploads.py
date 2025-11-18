"""
Audio file upload endpoints
"""
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

router = APIRouter()


@router.post("/{session_id}/upload", status_code=status.HTTP_201_CREATED)
async def upload_audio_file(
    session_id: int,
    audio_file: UploadFile = File(...),
    user_id: int = 1,  # TODO: Get from JWT token
    db: AsyncSession = Depends(get_db),
):
    """
    Upload audio file for a session

    - Updates session status to "uploading"
    - Saves file temporarily (will be moved to S3 in future)
    - Creates AudioFile record
    - Updates session status to "processing"
    """
    # Validate file type
    if not audio_file.content_type or not audio_file.content_type.startswith("audio/"):
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    # Check if audio file already exists
    existing_audio = await db.execute(
        select(AudioFile).where(AudioFile.session_id == session_id)
    )
    if existing_audio.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Audio file already uploaded for this session",
        )

    # Generate unique filename
    file_extension = Path(audio_file.filename or "recording.webm").suffix
    unique_filename = f"{session_id}_{uuid.uuid4().hex}{file_extension}"

    # Generate S3 key (path in bucket)
    s3_key = f"audio/{user_id}/{session_id}/{unique_filename}"

    # Create temporary file for upload
    temp_file = None
    s3_url = None

    try:
        # Save to temporary file first
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
            shutil.copyfileobj(audio_file.file, temp_file)
            temp_file_path = temp_file.name

        # Get file size
        file_size = os.path.getsize(temp_file_path)

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
            except Exception as e:
                # Fall back to local storage if S3 fails
                print(f"S3 upload failed, falling back to local: {e}")
                local_dir = Path("uploads")
                local_dir.mkdir(exist_ok=True)
                local_path = local_dir / unique_filename
                shutil.copy(temp_file_path, local_path)
                storage_type = "local"
                file_path = str(local_path)
        else:
            # Local storage (development mode)
            local_dir = Path("uploads")
            local_dir.mkdir(exist_ok=True)
            local_path = local_dir / unique_filename
            shutil.copy(temp_file_path, local_path)
            storage_type = "local"
            file_path = str(local_path)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}",
        )
    finally:
        # Clean up temporary file
        if temp_file and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)

    # Create AudioFile record
    audio_file_record = AudioFile(
        session_id=session_id,
        filename=unique_filename,
        file_path=file_path,  # S3 URL or local path
        file_size=file_size,
        mime_type=audio_file.content_type,
        duration_seconds=None,  # Will be extracted later
        storage_type=storage_type,
    )

    db.add(audio_file_record)

    # Update session status
    session.status = SessionStatus.PROCESSING

    await db.commit()
    await db.refresh(audio_file_record)

    return {
        "id": audio_file_record.id,
        "session_id": session_id,
        "filename": unique_filename,
        "file_size": file_size,
        "mime_type": audio_file.content_type,
        "storage_type": storage_type,
        "file_path": file_path if storage_type == "s3" else None,  # Only expose S3 URLs
        "message": f"Audio file uploaded successfully to {storage_type}. Processing will begin shortly.",
    }


@router.get("/{session_id}/audio")
async def get_audio_file_info(
    session_id: int,
    user_id: int = 1,  # TODO: Get from JWT token
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
