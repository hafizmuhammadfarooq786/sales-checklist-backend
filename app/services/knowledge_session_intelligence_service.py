"""Phase 3 session intelligence: next-best answers, coaching, technical risks, selling tools."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.checklist import ChecklistItem
from app.models.organization_knowledge import OrganizationKnowledgeDocument
from app.models.session import Session, SessionResponse, Transcript
from app.models.session_checklist_context import SessionChecklistItemContext
from app.models.session_knowledge_insight import SessionKnowledgeInsight
from app.services.knowledge_embedding import embed_texts
from app.services.knowledge_rag_service import _load_org_chunks, _rank_chunks, is_knowledge_base_enabled
from app.services.openai_compat import chat_completion_kwargs

logger = logging.getLogger(__name__)

SELLING_TOOL_TYPES = {
    "executive_summary",
    "contractor_talking_points",
    "architect_summary",
    "objection_handling",
    "battle_card",
    "roi_summary",
}

SELLING_TOOL_LABELS = {
    "executive_summary": "Executive summary",
    "contractor_talking_points": "Contractor talking points",
    "architect_summary": "Architect summary",
    "objection_handling": "Objection handling guide",
    "battle_card": "Competitive battle card",
    "roi_summary": "ROI summary",
}


async def get_session_insight(
    db: AsyncSession,
    session_id: int,
) -> SessionKnowledgeInsight | None:
    result = await db.execute(
        select(SessionKnowledgeInsight).where(
            SessionKnowledgeInsight.session_id == session_id
        )
    )
    return result.scalar_one_or_none()


async def analyze_session_intelligence(
    db: AsyncSession,
    *,
    organization_id: int,
    session: Session,
) -> dict:
    enabled = await is_knowledge_base_enabled(db, organization_id)
    if not enabled:
        payload = _empty_insight_payload(enabled=False)
        await _upsert_insight(db, session.id, organization_id, payload)
        return payload

    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    session_bundle = await _load_session_bundle(db, session.id)
    retrieval_query = _build_session_retrieval_query(session, session_bundle)
    query_embedding = embed_texts([retrieval_query])[0]
    chunks = await _load_org_chunks(db, organization_id)
    ranked = _rank_chunks(chunks, query_embedding, settings.KNOWLEDGE_BASE_RAG_TOP_K)

    context_blocks = []
    for chunk, _score in ranked:
        doc_name = chunk.document.original_filename if chunk.document else "Document"
        context_blocks.append(f"[Document: {doc_name}]\n{chunk.content}")
    approved_content = "\n\n---\n\n".join(context_blocks) if context_blocks else "No indexed content matched."

    parsed = await _generate_session_analysis(
        session=session,
        session_bundle=session_bundle,
        approved_content=approved_content,
    )

    technical_risks = parsed.get("technical_risks") or []
    has_technical_risk = any(
        str(risk.get("severity", "")).lower() in {"high", "medium"}
        for risk in technical_risks
        if isinstance(risk, dict)
    )

    payload = {
        "knowledge_base_enabled": True,
        "next_best_answers": parsed.get("next_best_answers") or [],
        "embedded_coaching": parsed.get("embedded_coaching") or [],
        "technical_risks": technical_risks,
        "summary_text": parsed.get("summary_text") or "",
        "has_technical_risk": has_technical_risk,
        "analyzed_at": datetime.now(timezone.utc),
    }
    await _upsert_insight(db, session.id, organization_id, payload)
    return payload


async def get_embedded_coaching_for_item(
    db: AsyncSession,
    *,
    organization_id: int,
    session: Session,
    checklist_item_id: int,
    trigger: str = "no",
    deal_context: str | None = None,
) -> dict:
    enabled = await is_knowledge_base_enabled(db, organization_id)
    if not enabled:
        return {
            "knowledge_base_enabled": False,
            "checklist_item_id": checklist_item_id,
            "trigger": trigger,
            "prompts": [
                "Organization knowledge intelligence is not enabled yet.",
            ],
        }

    item = await db.get(ChecklistItem, checklist_item_id)
    if not item:
        raise ValueError("Checklist item not found")

    session_bundle = await _load_session_bundle(db, session.id)
    item_context = next(
        (c for c in session_bundle["contexts"] if c["checklist_item_id"] == checklist_item_id),
        None,
    )
    context_text = deal_context or (item_context["deal_context"] if item_context else "")

    retrieval_query = (
        f"Checklist item: {item.title}\n"
        f"Definition: {item.definition}\n"
        f"Trigger: rep selected {trigger}\n"
        f"Deal context: {context_text}\n"
        f"Opportunity: {session.opportunity_name}"
    )
    query_embedding = embed_texts([retrieval_query])[0]
    chunks = await _load_org_chunks(db, organization_id)
    ranked = _rank_chunks(chunks, query_embedding, max(4, settings.KNOWLEDGE_BASE_RAG_TOP_K - 2))
    approved_content = "\n\n---\n\n".join(
        chunk.content for chunk, _ in ranked
    ) or "No matching approved content."

    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    completion = await client.chat.completions.create(
        model=settings.OPENAI_MODEL_GPT,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a sales coach. Return valid JSON with key prompts (array of 3-5 short "
                    "coaching questions the rep should ask or validate next). Use ONLY approved "
                    "company content. Be specific to the checklist item and deal context."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Item: {item.title}\n"
                    f"Definition: {item.definition}\n"
                    f"Trigger: {trigger}\n"
                    f"Deal context: {context_text or 'N/A'}\n"
                    f"Opportunity: {session.opportunity_name}\n"
                    f"Checklist state:\n{json.dumps(session_bundle['responses'], indent=2)}\n\n"
                    f"Approved content:\n{approved_content}"
                ),
            },
        ],
        response_format={"type": "json_object"},
        **chat_completion_kwargs(settings.OPENAI_MODEL_GPT, max_output_tokens=700, temperature=0.3),
    )
    raw = (completion.choices[0].message.content or "").strip()
    try:
        data = json.loads(raw)
        prompts = data.get("prompts") or []
    except json.JSONDecodeError:
        prompts = [
            f"What evidence do you still need to validate '{item.title}'?",
            "Which stakeholder still needs to confirm this requirement?",
        ]

    prompts = [str(p).strip() for p in prompts if str(p).strip()][:5]
    return {
        "knowledge_base_enabled": True,
        "checklist_item_id": checklist_item_id,
        "trigger": trigger,
        "prompts": prompts,
    }


async def generate_selling_tool(
    db: AsyncSession,
    *,
    organization_id: int,
    document_id: int,
    tool_type: str,
) -> dict:
    if tool_type not in SELLING_TOOL_TYPES:
        raise ValueError(f"Unsupported tool type: {tool_type}")

    enabled = await is_knowledge_base_enabled(db, organization_id)
    if not enabled:
        return {
            "knowledge_base_enabled": False,
            "tool_type": tool_type,
            "tool_label": SELLING_TOOL_LABELS.get(tool_type, tool_type),
            "content": "Organization knowledge base is not enabled yet.",
            "document_id": document_id,
            "document_name": "",
        }

    document = await db.get(OrganizationKnowledgeDocument, document_id)
    if not document or document.organization_id != organization_id:
        raise ValueError("Document not found")

    from app.models.organization_knowledge import OrganizationKnowledgeChunk

    result = await db.execute(
        select(OrganizationKnowledgeChunk)
        .where(OrganizationKnowledgeChunk.document_id == document_id)
        .order_by(OrganizationKnowledgeChunk.chunk_index.asc())
    )
    chunks = list(result.scalars().all())
    source_text = "\n\n".join(chunk.content for chunk in chunks).strip()
    if not source_text:
        raise ValueError("Document has no indexed content")

    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    label = SELLING_TOOL_LABELS[tool_type]
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    completion = await client.chat.completions.create(
        model=settings.OPENAI_MODEL_GPT,
        messages=[
            {
                "role": "system",
                "content": (
                    "Transform approved company technical content into practical sales material. "
                    "Use ONLY the provided source document. Do not invent specifications."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Create a {label} from this document ({document.original_filename}).\n\n"
                    f"Source:\n{source_text[:12000]}"
                ),
            },
        ],
        **chat_completion_kwargs(settings.OPENAI_MODEL_GPT, max_output_tokens=1200, temperature=0.3),
    )
    content = (completion.choices[0].message.content or "").strip()
    return {
        "knowledge_base_enabled": True,
        "tool_type": tool_type,
        "tool_label": label,
        "content": content or "Could not generate selling tool content.",
        "document_id": document_id,
        "document_name": document.original_filename,
    }


async def _load_session_bundle(db: AsyncSession, session_id: int) -> dict[str, Any]:
    responses_result = await db.execute(
        select(SessionResponse, ChecklistItem)
        .join(ChecklistItem, ChecklistItem.id == SessionResponse.item_id)
        .where(SessionResponse.session_id == session_id)
        .order_by(ChecklistItem.order.asc())
    )
    responses = []
    for response, item in responses_result.all():
        final_answer = response.user_answer if response.user_answer is not None else response.ai_answer
        responses.append(
            {
                "checklist_item_id": item.id,
                "order": item.order,
                "title": item.title,
                "answer": "yes" if final_answer else "no",
                "score": response.score,
            }
        )

    contexts_result = await db.execute(
        select(SessionChecklistItemContext).where(
            SessionChecklistItemContext.session_id == session_id
        )
    )
    contexts = [
        {
            "checklist_item_id": row.checklist_item_id,
            "deal_context": row.deal_context,
        }
        for row in contexts_result.scalars().all()
        if row.deal_context
    ]

    transcript_result = await db.execute(
        select(Transcript).where(Transcript.session_id == session_id)
    )
    transcript = transcript_result.scalar_one_or_none()
    transcript_excerpt = (transcript.text[:4000] if transcript and transcript.text else "")

    return {
        "responses": responses,
        "contexts": contexts,
        "transcript_excerpt": transcript_excerpt,
    }


def _build_session_retrieval_query(session: Session, bundle: dict[str, Any]) -> str:
    no_items = [r["title"] for r in bundle["responses"] if r["answer"] == "no"]
    context_lines = [
        c["deal_context"] for c in bundle["contexts"] if c.get("deal_context")
    ]
    parts = [
        f"Opportunity: {session.opportunity_name}",
        f"Customer: {session.customer_name}",
        f"Deal stage: {session.deal_stage or 'unknown'}",
        f"Checklist gaps: {', '.join(no_items) if no_items else 'none'}",
        f"Deal contexts: {' | '.join(context_lines) if context_lines else 'none'}",
    ]
    if bundle["transcript_excerpt"]:
        parts.append(f"Transcript excerpt: {bundle['transcript_excerpt'][:1500]}")
    return "\n".join(parts)


async def _generate_session_analysis(
    *,
    session: Session,
    session_bundle: dict[str, Any],
    approved_content: str,
) -> dict[str, Any]:
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    completion = await client.chat.completions.create(
        model=settings.OPENAI_MODEL_GPT,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a B2B sales intelligence analyst. Return valid JSON with keys: "
                    "summary_text (string), next_best_answers (array of {title, action, rationale, checklist_item_order}), "
                    "embedded_coaching (array of {checklist_item_order, prompts[]}), "
                    "technical_risks (array of {title, severity, description, checklist_item_orders[]}). "
                    "Use ONLY approved company content for recommendations. "
                    "Flag technical_risks when critical company differentiation topics appear missing from validation."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Session:\n"
                    f"Opportunity: {session.opportunity_name}\n"
                    f"Customer: {session.customer_name}\n"
                    f"Stage: {session.deal_stage or 'unknown'}\n\n"
                    f"Checklist:\n{json.dumps(session_bundle['responses'], indent=2)}\n\n"
                    f"Item contexts:\n{json.dumps(session_bundle['contexts'], indent=2)}\n\n"
                    f"Transcript excerpt:\n{session_bundle['transcript_excerpt'] or 'N/A'}\n\n"
                    f"Approved company content:\n{approved_content}"
                ),
            },
        ],
        response_format={"type": "json_object"},
        **chat_completion_kwargs(settings.OPENAI_MODEL_GPT, max_output_tokens=1400, temperature=0.25),
    )
    raw = (completion.choices[0].message.content or "").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Failed to parse session intelligence JSON")
        return {
            "summary_text": "Analysis could not be fully generated.",
            "next_best_answers": [],
            "embedded_coaching": [],
            "technical_risks": [],
        }


def _empty_insight_payload(*, enabled: bool) -> dict:
    return {
        "knowledge_base_enabled": enabled,
        "next_best_answers": [],
        "embedded_coaching": [],
        "technical_risks": [],
        "summary_text": (
            "Organization knowledge intelligence is not enabled."
            if not enabled
            else ""
        ),
        "has_technical_risk": False,
        "analyzed_at": datetime.now(timezone.utc),
    }


async def _upsert_insight(
    db: AsyncSession,
    session_id: int,
    organization_id: int,
    payload: dict,
) -> SessionKnowledgeInsight:
    row = await get_session_insight(db, session_id)
    analyzed_at = payload.get("analyzed_at") or datetime.now(timezone.utc)
    if row:
        row.organization_id = organization_id
        row.next_best_answers = payload.get("next_best_answers") or []
        row.embedded_coaching = payload.get("embedded_coaching") or []
        row.technical_risks = payload.get("technical_risks") or []
        row.summary_text = payload.get("summary_text")
        row.has_technical_risk = bool(payload.get("has_technical_risk"))
        row.knowledge_base_enabled = bool(payload.get("knowledge_base_enabled"))
        row.analyzed_at = analyzed_at
    else:
        row = SessionKnowledgeInsight(
            session_id=session_id,
            organization_id=organization_id,
            next_best_answers=payload.get("next_best_answers") or [],
            embedded_coaching=payload.get("embedded_coaching") or [],
            technical_risks=payload.get("technical_risks") or [],
            summary_text=payload.get("summary_text"),
            has_technical_risk=bool(payload.get("has_technical_risk")),
            knowledge_base_enabled=bool(payload.get("knowledge_base_enabled")),
            analyzed_at=analyzed_at,
        )
        db.add(row)
    await db.flush()
    await db.refresh(row)
    return row


async def run_session_intelligence_job(session_id: int, organization_id: int) -> None:
    """Background job entrypoint."""
    from app.db.session import get_db_session

    async with get_db_session() as db:
        session = await db.get(Session, session_id)
        if not session:
            return
        enabled = await is_knowledge_base_enabled(db, organization_id)
        if not enabled:
            return
        try:
            await analyze_session_intelligence(
                db,
                organization_id=organization_id,
                session=session,
            )
            await db.commit()
        except Exception:
            logger.exception("Session intelligence analysis failed for session %s", session_id)
            await db.rollback()
