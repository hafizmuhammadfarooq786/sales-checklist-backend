"""Celery tasks for knowledge base document ingestion."""
import asyncio
import logging

from app.celery_app import celery_app
from app.services.knowledge_ingestion_service import process_knowledge_document
from app.services.knowledge_session_intelligence_service import run_session_intelligence_job

logger = logging.getLogger(__name__)


@celery_app.task(name="knowledge_base.process_document", bind=True, max_retries=0)
def process_knowledge_document_task(self, document_id: int) -> None:
    """Index a knowledge document in a worker process."""
    logger.info("Celery: indexing knowledge document %s", document_id)
    asyncio.run(process_knowledge_document(document_id))
    logger.info("Celery: finished indexing knowledge document %s", document_id)


@celery_app.task(name="knowledge_base.analyze_session", bind=True, max_retries=0)
def analyze_session_intelligence_task(self, session_id: int, organization_id: int) -> None:
    """Analyze a session for next-best answers and technical risks."""
    logger.info("Celery: analyzing session intelligence %s", session_id)
    asyncio.run(run_session_intelligence_job(session_id, organization_id))
    logger.info("Celery: finished session intelligence %s", session_id)
