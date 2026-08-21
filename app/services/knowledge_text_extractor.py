"""Extract plain text from uploaded knowledge base files."""
from __future__ import annotations

import logging
from io import BytesIO

logger = logging.getLogger(__name__)

_ALLOWED_TYPES = {
    "application/pdf": "pdf",
    "text/plain": "text",
    "text/markdown": "text",
    "application/msword": "docx",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
}


def normalize_content_type(content_type: str) -> str:
    return (content_type or "").split(";")[0].strip().lower()


def is_allowed_knowledge_content_type(content_type: str) -> bool:
    return normalize_content_type(content_type) in _ALLOWED_TYPES


def extract_text_from_bytes(file_bytes: bytes, content_type: str) -> str:
    normalized = normalize_content_type(content_type)
    kind = _ALLOWED_TYPES.get(normalized)
    if not kind:
        raise ValueError(f"Unsupported file type: {content_type}")

    if kind == "text":
        return _extract_text_file(file_bytes)
    if kind == "pdf":
        return _extract_pdf(file_bytes)
    return _extract_docx(file_bytes)


def _extract_text_file(file_bytes: bytes) -> str:
    for encoding in ("utf-8", "utf-16", "latin-1"):
        try:
            text = file_bytes.decode(encoding)
            cleaned = text.strip()
            if cleaned:
                return cleaned
        except UnicodeDecodeError:
            continue
    raise ValueError("Could not decode text file")


def _extract_pdf(file_bytes: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(BytesIO(file_bytes))
    pages: list[str] = []
    for page in reader.pages:
        page_text = page.extract_text() or ""
        if page_text.strip():
            pages.append(page_text.strip())
    text = "\n\n".join(pages).strip()
    if not text:
        raise ValueError("No extractable text found in PDF")
    return text


def _extract_docx(file_bytes: bytes) -> str:
    from docx import Document

    document = Document(BytesIO(file_bytes))
    paragraphs = [p.text.strip() for p in document.paragraphs if p.text and p.text.strip()]
    text = "\n\n".join(paragraphs).strip()
    if not text:
        raise ValueError("No extractable text found in Word document")
    return text
