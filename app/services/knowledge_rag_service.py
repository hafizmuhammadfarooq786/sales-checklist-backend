"""Retrieval-augmented Q&A over organization knowledge base."""
from __future__ import annotations

import logging
from typing import List

from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.organization_knowledge import (
    KnowledgeBaseStatus,
    OrganizationKnowledgeChunk,
    OrganizationKnowledgeDocument,
)
from app.models.organization_settings import OrganizationSettings
from app.services.knowledge_embedding import cosine_similarity, embed_texts
from app.services.openai_compat import chat_completion_kwargs

logger = logging.getLogger(__name__)


async def is_knowledge_base_enabled(db: AsyncSession, organization_id: int) -> bool:
    result = await db.execute(
        select(OrganizationSettings.knowledge_base_status).where(
            OrganizationSettings.organization_id == organization_id
        )
    )
    status = result.scalar_one_or_none()
    if isinstance(status, KnowledgeBaseStatus):
        return status == KnowledgeBaseStatus.READY
    return status == KnowledgeBaseStatus.READY.value


async def ask_organization_knowledge(
    db: AsyncSession,
    *,
    organization_id: int,
    question: str,
    opportunity_name: str | None = None,
) -> dict:
    enabled = await is_knowledge_base_enabled(db, organization_id)
    if not enabled:
        return {
            "answer": (
                "Organization knowledge intelligence is not enabled yet. "
                "An administrator must upload and index the company knowledge base first."
            ),
            "citations": [],
            "knowledge_base_enabled": False,
        }

    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    query_embedding = embed_texts([question])[0]
    chunks = await _load_org_chunks(db, organization_id)
    ranked = _rank_chunks(chunks, query_embedding, settings.KNOWLEDGE_BASE_RAG_TOP_K)

    if not ranked:
        return {
            "answer": (
                "I could not find relevant approved company content for that question. "
                "Try rephrasing or ask your administrator to add more documents."
            ),
            "citations": [],
            "knowledge_base_enabled": True,
        }

    context_blocks = []
    citations = []
    for chunk, _score in ranked:
        doc_name = chunk.document.original_filename if chunk.document else "Document"
        context_blocks.append(
            f"[Document: {doc_name}]\n{chunk.content}"
        )
        citations.append(
            {
                "document_id": chunk.document_id,
                "document_name": doc_name,
                "excerpt": chunk.content[:500],
            }
        )

    context_text = "\n\n---\n\n".join(context_blocks)
    deal_line = f"Deal / opportunity: {opportunity_name}\n" if opportunity_name else ""

    system_prompt = (
        "You are a sales enablement assistant for a B2B organization. "
        "Answer ONLY using the provided approved company content. "
        "If the content does not contain enough information, say so clearly. "
        "Do not use outside knowledge or invent specifications. "
        "Be concise, practical, and oriented toward helping the salesperson move the deal forward."
    )
    user_prompt = (
        f"{deal_line}"
        f"Question:\n{question}\n\n"
        f"Approved company content:\n{context_text}"
    )

    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    completion = await client.chat.completions.create(
        model=settings.OPENAI_MODEL_GPT,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        **chat_completion_kwargs(settings.OPENAI_MODEL_GPT, max_output_tokens=900, temperature=0.2),
    )
    answer = (completion.choices[0].message.content or "").strip()
    if not answer:
        answer = (
            "I could not generate an answer from the approved company content. "
            "Please try a more specific question."
        )

    return {
        "answer": answer,
        "citations": citations,
        "knowledge_base_enabled": True,
    }


async def _load_org_chunks(
    db: AsyncSession,
    organization_id: int,
) -> List[OrganizationKnowledgeChunk]:
    result = await db.execute(
        select(OrganizationKnowledgeChunk)
        .where(OrganizationKnowledgeChunk.organization_id == organization_id)
        .options(selectinload(OrganizationKnowledgeChunk.document))
    )
    return list(result.scalars().all())


def _rank_chunks(
    chunks: List[OrganizationKnowledgeChunk],
    query_embedding: List[float],
    top_k: int,
) -> List[tuple[OrganizationKnowledgeChunk, float]]:
    scored: list[tuple[OrganizationKnowledgeChunk, float]] = []
    for chunk in chunks:
        embedding = chunk.embedding or []
        score = cosine_similarity(query_embedding, embedding)
        if score >= 0:
            scored.append((chunk, score))
    scored.sort(key=lambda item: item[1], reverse=True)
    return scored[:top_k]
