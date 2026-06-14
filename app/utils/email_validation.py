"""Email address validation for API inputs."""
from __future__ import annotations

import re
from typing import Optional

# Requires local part, domain, and at least one dot in the domain (TLD).
EMAIL_PATTERN = re.compile(
    r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
    r"(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$"
)


def validate_email_address(value: Optional[str], *, required: bool = True) -> Optional[str]:
    """Normalize and validate an email address. Raises ValueError when invalid."""
    if value is None or not str(value).strip():
        if required:
            raise ValueError("Email is required")
        return None

    cleaned = str(value).strip().lower()
    if not EMAIL_PATTERN.match(cleaned):
        raise ValueError("Please enter a valid email address")
    return cleaned
