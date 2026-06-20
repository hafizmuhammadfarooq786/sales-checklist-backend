"""Chunking and embedding for organization knowledge documents."""
from __future__ import annotations

import logging
import math
from typing import Iterable, List

from openai import OpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)


def chunk_text(text: str) -> List[str]:
    size = settings.KNOWLEDGE_BASE_CHUNK_SIZE
    overlap = settings.KNOWLEDGE_BASE_CHUNK_OVERLAP
    if size <= 0:
        return [text.strip()] if text.strip() else []

    cleaned = " ".join(text.split())
    if not cleaned:
        return []

    chunks: list[str] = []
    start = 0
    while start < len(cleaned):
        end = min(start + size, len(cleaned))
        piece = cleaned[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(cleaned):
            break
        start = max(end - overlap, start + 1)
    return chunks


def embed_texts(texts: Iterable[str]) -> List[List[float]]:
    items = [text for text in texts if text and text.strip()]
    if not items:
        return []

    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    response = client.embeddings.create(
        model=settings.OPENAI_MODEL_EMBEDDING,
        input=items,
    )
    return [row.embedding for row in response.data]


def cosine_similarity(left: List[float], right: List[float]) -> float:
    if not left or not right or len(left) != len(right):
        return -1.0
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return -1.0
    return dot / (left_norm * right_norm)
