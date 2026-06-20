"""Ingest organization knowledge documents into searchable chunks."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db_session
from app.models.organization_knowledge import (
    KnowledgeBaseStatus,
    KnowledgeDocumentStatus,
    OrganizationKnowledgeChunk,
    OrganizationKnowledgeDocument,
)
from app.models.organization_settings import OrganizationSettings
from app.services.knowledge_embedding import chunk_text, embed_texts
from app.services.knowledge_text_extractor import extract_text_from_bytes
from app.services.s3_service import get_s3_service

logger = logging.getLogger(__name__)


async def process_knowledge_document(document_id: int) -> None:
    """Full ingestion pipeline for a single document."""
    async with get_db_session() as db:
        document = await db.get(OrganizationKnowledgeDocument, document_id)
        if not document:
            logger.warning("Knowledge document %s not found", document_id)
            return

        org_settings = await _get_org_settings(db, document.organization_id)
        org_settings.knowledge_base_status = KnowledgeBaseStatus.PROCESSING
        org_settings.knowledge_base_error_message = None
        document.status = KnowledgeDocumentStatus.PROCESSING
        document.error_message = None
        await db.commit()

        try:
            file_bytes = await _load_document_bytes(document)
            text = extract_text_from_bytes(file_bytes, document.content_type)
            chunks = chunk_text(text)
            if not chunks:
                raise ValueError("Document contains no indexable text")

            embeddings = embed_texts(chunks)
            if len(embeddings) != len(chunks):
                raise RuntimeError("Embedding count mismatch")

            await db.execute(
                delete(OrganizationKnowledgeChunk).where(
                    OrganizationKnowledgeChunk.document_id == document.id
                )
            )

            for index, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                db.add(
                    OrganizationKnowledgeChunk(
                        organization_id=document.organization_id,
                        document_id=document.id,
                        chunk_index=index,
                        content=chunk,
                        embedding=embedding,
                        token_estimate=max(1, len(chunk) // 4),
                    )
                )

            document.status = KnowledgeDocumentStatus.INDEXED
            document.chunk_count = len(chunks)
            document.error_message = None
            await db.commit()
            await _refresh_org_knowledge_status(db, document.organization_id)
            logger.info(
                "Indexed knowledge document %s with %s chunks",
                document_id,
                len(chunks),
            )
        except Exception as exc:
            logger.exception("Failed to index knowledge document %s", document_id)
            await db.rollback()
            document = await db.get(OrganizationKnowledgeDocument, document_id)
            if document:
                document.status = KnowledgeDocumentStatus.FAILED
                document.error_message = str(exc)[:2000]
                await db.commit()
                await _refresh_org_knowledge_status(db, document.organization_id)


async def _load_document_bytes(document: OrganizationKnowledgeDocument) -> bytes:
    if document.s3_key.startswith("uploads/"):
        local_path = Path(document.s3_key)
        if not local_path.exists():
            raise FileNotFoundError(f"Local knowledge file not found: {document.s3_key}")
        return local_path.read_bytes()

    from fastapi.concurrency import run_in_threadpool

    s3_service = get_s3_service()
    return await run_in_threadpool(s3_service.get_object_bytes, document.s3_key)


async def store_knowledge_file(
    *,
    organization_id: int,
    uploaded_by_user_id: int,
    original_filename: str,
    content_type: str,
    file_bytes: bytes,
) -> OrganizationKnowledgeDocument:
    ext = Path(original_filename).suffix or ".bin"
    s3_key = f"knowledge-base/{organization_id}/{uuid.uuid4().hex}{ext}"
    s3_url: str | None = None

    try:
        s3_service = get_s3_service()
        uploaded_key = await s3_service.upload_bytes(
            file_bytes,
            s3_key,
            content_type=content_type,
        )
        s3_url = (
            f"https://{s3_service.bucket_name}.s3.{settings.AWS_REGION}.amazonaws.com/{uploaded_key}"
        )
        s3_key = uploaded_key
    except Exception:
        local_path = Path(f"uploads/{s3_key}")
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(file_bytes)
        s3_key = str(local_path)
        s3_url = None

    async with get_db_session() as db:
        org_settings = await _get_org_settings(db, organization_id)
        if org_settings.knowledge_base_status == KnowledgeBaseStatus.NOT_STARTED:
            org_settings.knowledge_base_status = KnowledgeBaseStatus.PROCESSING

        document = OrganizationKnowledgeDocument(
            organization_id=organization_id,
            uploaded_by_user_id=uploaded_by_user_id,
            original_filename=original_filename,
            content_type=content_type,
            file_size_bytes=len(file_bytes),
            s3_key=s3_key,
            s3_url=s3_url,
            status=KnowledgeDocumentStatus.QUEUED,
        )
        db.add(document)
        await db.commit()
        await db.refresh(document)
        return document


async def delete_knowledge_document(db: AsyncSession, document: OrganizationKnowledgeDocument) -> None:
    if not document.s3_key.startswith("uploads/"):
        try:
            s3_service = get_s3_service()
            s3_service.delete_file(document.s3_key)
        except Exception:
            logger.warning("Could not delete S3 object %s", document.s3_key)
    else:
        local_path = Path(document.s3_key)
        if local_path.exists():
            local_path.unlink()

    organization_id = document.organization_id
    await db.delete(document)
    await db.commit()
    await _refresh_org_knowledge_status(db, organization_id)


async def _get_org_settings(db: AsyncSession, organization_id: int) -> OrganizationSettings:
    result = await db.execute(
        select(OrganizationSettings).where(
            OrganizationSettings.organization_id == organization_id
        )
    )
    org_settings = result.scalar_one_or_none()
    if not org_settings:
        org_settings = OrganizationSettings(
            organization_id=organization_id,
            allow_self_registration=False,
            default_role="rep",
            settings={},
            knowledge_base_status=KnowledgeBaseStatus.NOT_STARTED,
        )
        db.add(org_settings)
        await db.flush()
    return org_settings


async def _refresh_org_knowledge_status(db: AsyncSession, organization_id: int) -> None:
    org_settings = await _get_org_settings(db, organization_id)

    total_result = await db.execute(
        select(func.count())
        .select_from(OrganizationKnowledgeDocument)
        .where(OrganizationKnowledgeDocument.organization_id == organization_id)
    )
    total_count = int(total_result.scalar() or 0)

    indexed_result = await db.execute(
        select(func.count())
        .select_from(OrganizationKnowledgeDocument)
        .where(
            OrganizationKnowledgeDocument.organization_id == organization_id,
            OrganizationKnowledgeDocument.status == KnowledgeDocumentStatus.INDEXED,
        )
    )
    indexed_count = int(indexed_result.scalar() or 0)

    processing_result = await db.execute(
        select(func.count())
        .select_from(OrganizationKnowledgeDocument)
        .where(
            OrganizationKnowledgeDocument.organization_id == organization_id,
            OrganizationKnowledgeDocument.status.in_(
                [
                    KnowledgeDocumentStatus.QUEUED,
                    KnowledgeDocumentStatus.PROCESSING,
                ]
            ),
        )
    )
    processing_count = int(processing_result.scalar() or 0)

    failed_result = await db.execute(
        select(func.count())
        .select_from(OrganizationKnowledgeDocument)
        .where(
            OrganizationKnowledgeDocument.organization_id == organization_id,
            OrganizationKnowledgeDocument.status == KnowledgeDocumentStatus.FAILED,
        )
    )
    failed_count = int(failed_result.scalar() or 0)

    min_required = settings.KNOWLEDGE_BASE_MIN_INDEXED_DOCUMENTS

    if total_count == 0:
        org_settings.knowledge_base_status = KnowledgeBaseStatus.NOT_STARTED
        org_settings.knowledge_base_ready_at = None
        org_settings.knowledge_base_error_message = None
    elif indexed_count >= min_required and processing_count == 0:
        org_settings.knowledge_base_status = KnowledgeBaseStatus.READY
        if org_settings.knowledge_base_ready_at is None:
            org_settings.knowledge_base_ready_at = datetime.now(timezone.utc)
        org_settings.knowledge_base_error_message = None
    elif processing_count > 0:
        org_settings.knowledge_base_status = KnowledgeBaseStatus.PROCESSING
        org_settings.knowledge_base_error_message = None
    elif failed_count > 0 and indexed_count < min_required:
        org_settings.knowledge_base_status = KnowledgeBaseStatus.ERROR
        org_settings.knowledge_base_error_message = (
            "One or more documents failed to index. Fix or re-upload failed files."
        )
    else:
        org_settings.knowledge_base_status = KnowledgeBaseStatus.PROCESSING
        org_settings.knowledge_base_error_message = (
            f"Upload at least {min_required} successfully indexed document(s) to enable intelligence."
        )

    await db.commit()


async def get_knowledge_base_status(db: AsyncSession, organization_id: int) -> dict:
    org_settings = await _get_org_settings(db, organization_id)

    total_result = await db.execute(
        select(func.count())
        .select_from(OrganizationKnowledgeDocument)
        .where(OrganizationKnowledgeDocument.organization_id == organization_id)
    )
    total_count = int(total_result.scalar() or 0)

    indexed_result = await db.execute(
        select(func.count())
        .select_from(OrganizationKnowledgeDocument)
        .where(
            OrganizationKnowledgeDocument.organization_id == organization_id,
            OrganizationKnowledgeDocument.status == KnowledgeDocumentStatus.INDEXED,
        )
    )
    indexed_count = int(indexed_result.scalar() or 0)

    min_required = settings.KNOWLEDGE_BASE_MIN_INDEXED_DOCUMENTS
    status = org_settings.knowledge_base_status
    if isinstance(status, KnowledgeBaseStatus):
        status_value = status.value
    else:
        status_value = str(status)

    return {
        "status": status_value,
        "is_enabled": status_value == KnowledgeBaseStatus.READY.value,
        "indexed_document_count": indexed_count,
        "total_document_count": total_count,
        "min_documents_required": min_required,
        "ready_at": org_settings.knowledge_base_ready_at,
        "error_message": org_settings.knowledge_base_error_message,
    }
