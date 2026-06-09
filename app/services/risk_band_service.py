"""
Shared risk band classification logic.
"""
from app.models.scoring import RiskBand

AT_RISK_MAX_SCORE = 30
GOOD_MAX_SCORE = 60
EXCELLENT_MIN_SCORE = 61

# Backward-compatible aliases used by manager dashboard queries.
HEALTHY_MIN_SCORE = EXCELLENT_MIN_SCORE
GOOD_MIN_SCORE = 31


def get_risk_band(score: float) -> RiskBand:
    """
    Classify score into risk band.

    Rules:
    - 0-30: at risk (red)
    - 31-60: good (yellow)
    - 61-100: excellent (green)
    """
    if score <= AT_RISK_MAX_SCORE:
        return RiskBand.RED
    if score <= GOOD_MAX_SCORE:
        return RiskBand.YELLOW
    return RiskBand.GREEN


def get_risk_label(risk_band: RiskBand | str) -> str:
    """Human-readable label for risk band."""
    value = risk_band.value if hasattr(risk_band, "value") else risk_band
    labels = {
        "green": "Excellent",
        "yellow": "Good",
        "red": "At Risk",
    }
    return labels.get(value, "Unknown")
