"""Organization Knowledge Intelligence API endpoints."""
import logging

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_roles
from app.core.config import settings
from app.db.session import get_db
from app.models import User
from app.models.organization_knowledge import OrganizationKnowledgeDocument
from app.models.user import UserRole
from app.schemas.knowledge_base import (
    KnowledgeBaseStatusResponse,
    KnowledgeDocumentResponse,
    KnowledgeDocumentUploadResponse,
    SellingToolRequest,
    SellingToolResponse,
)
from app.services.knowledge_ingestion_service import (
    delete_knowledge_document,
    get_knowledge_base_status,
    process_knowledge_document,
    store_knowledge_file,
)
from app.services.knowledge_text_extractor import (
    is_allowed_knowledge_content_type,
    normalize_content_type,
)
from app.services.knowledge_session_intelligence_service import generate_selling_tool

logger = logging.getLogger(__name__)

router = APIRouter()


def _enqueue_document_processing(
    background_tasks: BackgroundTasks,
    document_id: int,
) -> None:
    if settings.USE_CELERY_FOR_KNOWLEDGE_BASE:
        try:
            from app.tasks.knowledge_base import process_knowledge_document_task

            process_knowledge_document_task.delay(document_id)
            return
        except Exception as exc:
            logger.warning(
                "Celery unavailable for knowledge base; falling back to BackgroundTasks: %s",
                exc,
            )
    background_tasks.add_task(process_knowledge_document, document_id)


def _require_org_id(user: User) -> int:
    if not user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not assigned to an organization",
        )
    return user.organization_id


@router.get("/status", response_model=KnowledgeBaseStatusResponse)
async def get_knowledge_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.MANAGER, UserRole.REP)
    ),
):
    """Return org knowledge base activation status for any org member."""
    organization_id = _require_org_id(current_user)
    payload = await get_knowledge_base_status(db, organization_id)
    return KnowledgeBaseStatusResponse(**payload)


@router.get("/documents", response_model=list[KnowledgeDocumentResponse])
async def list_knowledge_documents(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    organization_id = _require_org_id(current_user)
    result = await db.execute(
        select(OrganizationKnowledgeDocument)
        .where(OrganizationKnowledgeDocument.organization_id == organization_id)
        .order_by(OrganizationKnowledgeDocument.created_at.desc())
    )
    documents = result.scalars().all()
    return [KnowledgeDocumentResponse.model_validate(doc) for doc in documents]


@router.post("/documents", response_model=KnowledgeDocumentUploadResponse)
async def upload_knowledge_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    organization_id = _require_org_id(current_user)
    content_type = normalize_content_type(file.content_type or "")
    if not is_allowed_knowledge_content_type(content_type):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Supported types: PDF, DOCX, TXT, and Markdown",
        )

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")
    if len(file_bytes) > settings.KNOWLEDGE_BASE_MAX_FILE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File exceeds maximum allowed size",
        )

    document = await store_knowledge_file(
        organization_id=organization_id,
        uploaded_by_user_id=current_user.id,
        original_filename=file.filename or "document",
        content_type=content_type,
        file_bytes=file_bytes,
    )
    _enqueue_document_processing(background_tasks, document.id)

    return KnowledgeDocumentUploadResponse(
        document=KnowledgeDocumentResponse.model_validate(document),
        message="Document uploaded. Indexing has started.",
    )


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_knowledge_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    organization_id = _require_org_id(current_user)
    document = await db.get(OrganizationKnowledgeDocument, document_id)
    if not document or document.organization_id != organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    await delete_knowledge_document(db, document)


@router.post(
    "/documents/{document_id}/reprocess",
    response_model=KnowledgeDocumentUploadResponse,
)
async def reprocess_knowledge_document(
    document_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    organization_id = _require_org_id(current_user)
    document = await db.get(OrganizationKnowledgeDocument, document_id)
    if not document or document.organization_id != organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    _enqueue_document_processing(background_tasks, document.id)
    return KnowledgeDocumentUploadResponse(
        document=KnowledgeDocumentResponse.model_validate(document),
        message="Document reprocessing has started.",
    )


@router.post(
    "/documents/{document_id}/selling-tool",
    response_model=SellingToolResponse,
)
async def create_document_selling_tool(
    document_id: int,
    payload: SellingToolRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    organization_id = _require_org_id(current_user)
    document = await db.get(OrganizationKnowledgeDocument, document_id)
    if not document or document.organization_id != organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    try:
        result = await generate_selling_tool(
            db,
            organization_id=organization_id,
            document_id=document_id,
            tool_type=payload.tool_type,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return SellingToolResponse(**result)
