"""Load organization logo bytes from stored logo_url references."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import httpx

from app.services.s3_service import get_s3_service

logger = logging.getLogger(__name__)

_CONTENT_TYPE_BY_EXT = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


def guess_logo_content_type(logo_url: str) -> str:
    ext = Path(logo_url.split("?")[0]).suffix.lower()
    return _CONTENT_TYPE_BY_EXT.get(ext, "application/octet-stream")


def _extract_s3_key(reference: str) -> Optional[str]:
    """Normalize stored logo references to an S3 object key when possible."""
    ref = reference.strip()
    if not ref:
        return None
    if ref.startswith(("branding/", "pending-registrations/")):
        return ref
    if ".amazonaws.com/" in ref:
        return ref.split(".amazonaws.com/", 1)[1].split("?", 1)[0]
    if ref.startswith("s3://"):
        without_scheme = ref[5:]
        if "/" in without_scheme:
            return without_scheme.split("/", 1)[1]
    return None


async def load_organization_logo_bytes(logo_url: Optional[str]) -> Optional[bytes]:
    """Resolve logo bytes from http URL, S3 key, or local uploads path."""
    u = (logo_url or "").strip()
    if not u:
        return None

    if u.startswith(("http://", "https://")):
        s3_key = _extract_s3_key(u)
        if s3_key:
            try:
                return get_s3_service().get_object_bytes(s3_key)
            except Exception as exc:
                logger.warning("Failed to load logo from S3 key %s: %s", s3_key, exc)
        return await _fetch_http(u)

    s3_key = _extract_s3_key(u)
    if s3_key:
        try:
            return get_s3_service().get_object_bytes(s3_key)
        except Exception as exc:
            logger.warning("Failed to load logo from S3 key %s: %s", s3_key, exc)

    local_path = _resolve_local_path(u)
    if local_path:
        return local_path.read_bytes()

    return None


def _resolve_local_path(u: str) -> Optional[Path]:
    candidates: list[Path] = []

    path = Path(u)
    candidates.append(path)
    if not u.startswith("uploads/"):
        candidates.append(Path("uploads") / u.lstrip("/"))

    backend_root = Path(__file__).resolve().parents[2]
    candidates.append(backend_root / u)
    if not u.startswith("uploads/"):
        candidates.append(backend_root / "uploads" / u.lstrip("/"))

    for candidate in candidates:
        if candidate.is_file():
            return candidate

    return None


async def _fetch_http(url: str) -> Optional[bytes]:
    try:
        async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
            response = await client.get(url)
            if response.status_code != 200:
                return None
            content = response.content
            if not content or len(content) < 32:
                return None
            ctype = (response.headers.get("content-type") or "").lower()
            if ctype and not any(
                token in ctype
                for token in ("image", "octet-stream", "application/x-www-form-urlencoded")
            ):
                if "html" in ctype or "json" in ctype:
                    return None
            return content
    except Exception:
        return None
