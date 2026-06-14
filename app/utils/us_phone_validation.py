"""US phone validation: NANP structure + assigned geographic area codes."""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Optional

PHONE_DIGIT_COUNT = 10
PHONE_FORMATTED_PATTERN = re.compile(r"^\(\d{3}\) \d{3}-\d{4}$")


def _strip_leading_country_code(digits: str) -> str:
    if (
        digits.startswith("1")
        and len(digits) >= 2
        and "2" <= digits[1] <= "9"
    ):
        return digits[1:]
    return digits


def normalize_us_phone_digits(value: str) -> str:
    """Strip optional US country code (+1) and cap at 10 NANP digits."""
    digits = re.sub(r"\D", "", value)
    digits = _strip_leading_country_code(digits)
    while len(digits) > PHONE_DIGIT_COUNT:
        stripped = _strip_leading_country_code(digits)
        if stripped == digits:
            break
        digits = stripped
    return digits[:PHONE_DIGIT_COUNT]


@lru_cache(maxsize=1)
def _load_us_geographic_area_codes() -> frozenset[str]:
    data_path = Path(__file__).resolve().parent.parent / "data" / "us_geographic_area_codes.json"
    with data_path.open(encoding="utf-8") as handle:
        codes = json.load(handle)
    return frozenset(str(code) for code in codes)


def _valid_nanp_nxx(nxx: str) -> bool:
    """NXX prefix: leading digit 2-9, not N11."""
    if len(nxx) != 3:
        return False
    if nxx[0] in "01":
        return False
    if nxx[1:] == "11":
        return False
    return True


def validate_us_phone_digits(digits: str) -> Optional[str]:
    """Return an error message when invalid, otherwise None."""
    if len(digits) != PHONE_DIGIT_COUNT:
        return f"Phone number must be {PHONE_DIGIT_COUNT} digits"

    area = digits[:3]
    exchange = digits[3:6]
    subscriber = digits[6:10]

    if not _valid_nanp_nxx(area):
        return "Area code format is invalid"
    if area not in _load_us_geographic_area_codes():
        return "Enter a valid US area code"
    if not _valid_nanp_nxx(exchange):
        return "Phone number prefix is invalid"
    if exchange == "555" and "0100" <= subscriber <= "0199":
        return "Phone number is not assignable"

    return None


def validate_us_phone_value(value: Optional[str], *, required: bool = False) -> Optional[str]:
    """Validate formatted or raw phone input."""
    if value is None:
        return "Phone number is required" if required else None

    cleaned = value.strip()
    if not cleaned:
        return "Phone number is required" if required else None

    digits = normalize_us_phone_digits(cleaned)
    if PHONE_FORMATTED_PATTERN.match(cleaned):
        pass
    elif len(digits) == PHONE_DIGIT_COUNT:
        pass
    else:
        return "Use format (212) 456-7890"

    return validate_us_phone_digits(digits)
