"""Checklist-item intelligence using organization knowledge base."""
from __future__ import annotations

import json
import logging
from typing import Optional

from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.checklist import ChecklistItem
from app.models.checklist_behaviour import ChecklistItemBehaviour
from app.models.session import Session
from app.models.session_checklist_context import SessionChecklistItemContext
from app.services.knowledge_embedding import embed_texts
from app.services.knowledge_rag_service import _load_org_chunks, _rank_chunks, is_knowledge_base_enabled
from app.services.openai_compat import chat_completion_kwargs

logger = logging.getLogger(__name__)

_MAX_CONTEXT_LENGTH = 2000


async def list_session_contexts(
    db: AsyncSession,
    session_id: int,
) -> list[SessionChecklistItemContext]:
    result = await db.execute(
        select(SessionChecklistItemContext).where(
            SessionChecklistItemContext.session_id == session_id
        )
    )
    return list(result.scalars().all())


async def get_item_context(
    db: AsyncSession,
    session_id: int,
    checklist_item_id: int,
) -> Optional[SessionChecklistItemContext]:
    result = await db.execute(
        select(SessionChecklistItemContext).where(
            SessionChecklistItemContext.session_id == session_id,
            SessionChecklistItemContext.checklist_item_id == checklist_item_id,
        )
    )
    return result.scalar_one_or_none()


async def save_item_context(
    db: AsyncSession,
    session_id: int,
    checklist_item_id: int,
    deal_context: str | None,
) -> SessionChecklistItemContext:
    cleaned = (deal_context or "").strip()
    if len(cleaned) > _MAX_CONTEXT_LENGTH:
        cleaned = cleaned[:_MAX_CONTEXT_LENGTH]

    row = await get_item_context(db, session_id, checklist_item_id)
    if row:
        row.deal_context = cleaned or None
    else:
        row = SessionChecklistItemContext(
            session_id=session_id,
            checklist_item_id=checklist_item_id,
            deal_context=cleaned or None,
        )
        db.add(row)
    await db.flush()
    await db.refresh(row)
    return row


async def get_checklist_item_intelligence(
    db: AsyncSession,
    *,
    organization_id: int,
    session: Session,
    checklist_item_id: int,
    deal_context: str | None = None,
) -> dict:
    enabled = await is_knowledge_base_enabled(db, organization_id)
    if not enabled:
        return {
            "knowledge_base_enabled": False,
            "expertise_points": [],
            "yes_guidance": (
                "Organization knowledge intelligence is not enabled. "
                "An administrator must upload and index approved company documents first."
            ),
            "no_guidance": (
                "Without an active knowledge base, use the checklist definition and "
                "behavioral framework to decide when evidence is missing."
            ),
            "citations": [],
        }

    item = await db.get(ChecklistItem, checklist_item_id)
    if not item:
        raise ValueError("Checklist item not found")

    if deal_context is not None:
        await save_item_context(db, session.id, checklist_item_id, deal_context)
    else:
        stored = await get_item_context(db, session.id, checklist_item_id)
        deal_context = stored.deal_context if stored else None

    framework_summary = await _load_framework_summary(db, checklist_item_id)
    retrieval_query = _build_retrieval_query(
        item_title=item.title,
        item_definition=item.definition,
        deal_context=deal_context,
        opportunity_name=session.opportunity_name,
        deal_stage=session.deal_stage,
    )

    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    query_embedding = embed_texts([retrieval_query])[0]
    chunks = await _load_org_chunks(db, organization_id)
    ranked = _rank_chunks(chunks, query_embedding, settings.KNOWLEDGE_BASE_RAG_TOP_K)

    citations = []
    context_blocks = []
    for chunk, _score in ranked:
        doc_name = chunk.document.original_filename if chunk.document else "Document"
        context_blocks.append(f"[Document: {doc_name}]\n{chunk.content}")
        citations.append(
            {
                "document_id": chunk.document_id,
                "document_name": doc_name,
                "excerpt": chunk.content[:500],
            }
        )

    if not context_blocks:
        return {
            "knowledge_base_enabled": True,
            "expertise_points": [
                "No matching approved company content was found for this checklist item and deal context.",
                "Try adding more detail to the deal context or ask your administrator to upload relevant documents.",
            ],
            "yes_guidance": (
                f"Answer Yes only if you can validate '{item.title}' using evidence from the conversation "
                "and your company's approved standards."
            ),
            "no_guidance": (
                f"Answer No if required evidence for '{item.title}' has not been established yet."
            ),
            "citations": [],
        }

    context_text = "\n\n---\n\n".join(context_blocks)
    parsed = await _generate_structured_guidance(
        item_title=item.title,
        item_definition=item.definition,
        deal_context=deal_context,
        opportunity_name=session.opportunity_name,
        deal_stage=session.deal_stage,
        framework_summary=framework_summary,
        approved_content=context_text,
    )

    return {
        "knowledge_base_enabled": True,
        "expertise_points": parsed["expertise_points"],
        "yes_guidance": parsed["yes_guidance"],
        "no_guidance": parsed["no_guidance"],
        "citations": citations,
    }


def _build_retrieval_query(
    *,
    item_title: str,
    item_definition: str,
    deal_context: str | None,
    opportunity_name: str | None,
    deal_stage: str | None,
) -> str:
    parts = [
        f"Checklist item: {item_title}",
        f"Definition: {item_definition}",
    ]
    if deal_context:
        parts.append(f"Deal context: {deal_context}")
    if opportunity_name:
        parts.append(f"Opportunity: {opportunity_name}")
    if deal_stage:
        parts.append(f"Deal stage: {deal_stage}")
    return "\n".join(parts)


async def _load_framework_summary(db: AsyncSession, checklist_item_id: int) -> str:
    result = await db.execute(
        select(ChecklistItemBehaviour)
        .where(
            ChecklistItemBehaviour.checklist_item_id == checklist_item_id,
            ChecklistItemBehaviour.isactive.is_(True),
        )
        .order_by(ChecklistItemBehaviour.order)
    )
    rows = list(result.scalars().all())
    if not rows:
        return ""

    behavior = next((r for r in rows if r.rowtype == "Behavior"), None)
    reminder = next((r for r in rows if r.rowtype == "Reminder"), None)
    questions = [r.question for r in rows if r.rowtype == "Question" and r.question]

    lines: list[str] = []
    if behavior and behavior.behaviour:
        lines.append(f"Expected behavior: {behavior.behaviour}")
    if questions:
        lines.append("Evidence questions: " + "; ".join(questions[:5]))
    if reminder and reminder.keyreminder:
        lines.append(f"Key reminder: {reminder.keyreminder}")
    return "\n".join(lines)


async def _generate_structured_guidance(
    *,
    item_title: str,
    item_definition: str,
    deal_context: str | None,
    opportunity_name: str | None,
    deal_stage: str | None,
    framework_summary: str,
    approved_content: str,
) -> dict:
    deal_lines = []
    if opportunity_name:
        deal_lines.append(f"Opportunity: {opportunity_name}")
    if deal_stage:
        deal_lines.append(f"Deal stage: {deal_stage}")
    if deal_context:
        deal_lines.append(f"Rep-entered deal context: {deal_context}")

    system_prompt = (
        "You are a sales enablement assistant. Use ONLY the approved company content provided. "
        "Return valid JSON with exactly these keys: "
        "expertise_points (array of 2-5 short strings), yes_guidance (string), no_guidance (string). "
        "expertise_points should surface the most relevant company expertise for this checklist item and deal. "
        "yes_guidance should explain what evidence is required to answer Yes for THIS company on this item. "
        "no_guidance should explain when to answer No and what is missing. "
        "Do not invent facts not supported by the approved content."
    )
    user_prompt = (
        f"Checklist item: {item_title}\n"
        f"Item definition: {item_definition}\n"
        f"{chr(10).join(deal_lines)}\n\n"
        f"Behavioral framework:\n{framework_summary or 'N/A'}\n\n"
        f"Approved company content:\n{approved_content}"
    )

    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    completion = await client.chat.completions.create(
        model=settings.OPENAI_MODEL_GPT,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        **chat_completion_kwargs(settings.OPENAI_MODEL_GPT, max_output_tokens=1000, temperature=0.2),
    )

    raw = (completion.choices[0].message.content or "").strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Failed to parse checklist intelligence JSON: %s", raw[:300])
        return _fallback_guidance(item_title, item_definition)

    expertise_points = data.get("expertise_points") or []
    if not isinstance(expertise_points, list):
        expertise_points = [str(expertise_points)]
    expertise_points = [str(point).strip() for point in expertise_points if str(point).strip()]

    yes_guidance = str(data.get("yes_guidance") or "").strip()
    no_guidance = str(data.get("no_guidance") or "").strip()
    if not yes_guidance or not no_guidance:
        fallback = _fallback_guidance(item_title, item_definition)
        yes_guidance = yes_guidance or fallback["yes_guidance"]
        no_guidance = no_guidance or fallback["no_guidance"]

    return {
        "expertise_points": expertise_points[:5],
        "yes_guidance": yes_guidance,
        "no_guidance": no_guidance,
    }


def _fallback_guidance(item_title: str, item_definition: str) -> dict:
    return {
        "expertise_points": [
            f"Review company-approved content related to {item_title}.",
        ],
        "yes_guidance": (
            f"Answer Yes when you have validated: {item_definition}"
        ),
        "no_guidance": (
            f"Answer No when the required evidence for {item_title} has not been established."
        ),
    }
