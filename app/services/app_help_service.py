"""Fallback answering for in-app help questions the approved corpus does not cover.

The corpus itself lives in the frontend and is served from there verbatim; this
service only runs when nothing in it matched. The client sends the approved
entries it considered as context, and the model may answer ONLY from those.

This is deliberately narrow. The product promise is that help answers trace back
to approved content, so an unmatched question gets either a grounded answer drawn
from approved text or an honest "I don't know" — never invented app behaviour.
"""
from __future__ import annotations

import logging
from typing import AsyncIterator, Iterable

from openai import AsyncOpenAI

from app.core.config import settings
from app.services.openai_compat import chat_completion_kwargs

logger = logging.getLogger(__name__)

MAX_CONTEXT_ENTRIES = 12
MAX_QUESTION_CHARS = 500

# Reasoning models (gpt-5, o-series) spend this budget on internal reasoning
# BEFORE emitting any visible text, and a long grounding context pushes that
# reasoning cost up. A budget sized for the answer alone gets silently consumed,
# so the stream ends empty or truncated mid-sentence. The answer itself stays
# short — the headroom is for the reasoning in front of it.
MAX_OUTPUT_TOKENS = 3000

SYSTEM_PROMPT = (
    "You are the in-app help assistant for the Sales Checklist™ application. "
    "You explain HOW TO USE THE APP.\n\n"
    "Rules you must follow:\n"
    "1. Answer ONLY from the approved help content provided below. It is the sole "
    "source of truth about this application.\n"
    "2. If the approved content does not answer the question, say so plainly and "
    "suggest contacting their administrator. Never guess at app behaviour, never "
    "invent screens, buttons, menu items or features.\n"
    "3. Never advise on sales strategy, deal tactics, or what to tell a customer. "
    "That is outside app help.\n"
    "4. Be brief — a few sentences, or short numbered steps. The reader is working "
    "in the app while reading this.\n"
    "5. Refer to screens and controls using exactly the names used in the approved "
    "content.\n"
    "6. Where the approved content covers the question, mention which help topic "
    "it came from so the reader can open it."
)


def _format_context(entries: Iterable[dict]) -> str:
    blocks: list[str] = []
    for entry in list(entries)[:MAX_CONTEXT_ENTRIES]:
        question = str(entry.get("question", "")).strip()
        answer = str(entry.get("answer", "")).strip()
        source = str(entry.get("source", "")).strip()
        if not question or not answer:
            continue
        blocks.append(
            f"### Help topic: {question}\n{answer}\n(Source: {source})"
        )
    return "\n\n".join(blocks)


async def stream_app_help_answer(
    *,
    question: str,
    context_entries: list[dict],
    screen: str | None = None,
    role: str | None = None,
) -> AsyncIterator[str]:
    """Yield the answer in chunks so the panel can render it as it arrives."""
    question = (question or "").strip()[:MAX_QUESTION_CHARS]
    if not question:
        yield "Please enter a question."
        return

    if not settings.OPENAI_API_KEY:
        yield (
            "AI help is not configured on this environment. "
            "Please contact your administrator."
        )
        return

    context_text = _format_context(context_entries)
    if not context_text:
        yield (
            "I don't have approved help content to answer that from. "
            "Please contact your administrator."
        )
        return

    situation = []
    if role:
        situation.append(f"The user's role is {role}.")
    if screen:
        situation.append(f"They are on the {screen} screen.")

    user_prompt = (
        f"{' '.join(situation)}\n\n"
        f"Their question:\n{question}\n\n"
        f"Approved help content:\n{context_text}"
    )

    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    try:
        stream = await client.chat.completions.create(
            model=settings.OPENAI_MODEL_GPT,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            stream=True,
            **chat_completion_kwargs(
                settings.OPENAI_MODEL_GPT,
                max_output_tokens=MAX_OUTPUT_TOKENS,
                temperature=0.2,
            ),
        )
        produced = False
        async for chunk in stream:
            if not chunk.choices:
                continue
            piece = chunk.choices[0].delta.content
            if piece:
                produced = True
                yield piece
        if not produced:
            # The model returned no visible text — on reasoning models this means
            # the token budget went entirely to reasoning. Never leave the panel
            # showing an empty answer.
            logger.warning(
                "App help stream produced no content (model=%s, context=%d)",
                settings.OPENAI_MODEL_GPT,
                len(context_entries),
            )
            yield (
                "I could not produce an answer for that. Please try rephrasing, "
                "or contact your administrator."
            )
    except Exception:  # noqa: BLE001 - surfaced to the user, logged for us
        logger.exception("App help streaming failed")
        yield (
            "\n\nSomething went wrong generating that answer. "
            "Please try again, or contact your administrator."
        )
