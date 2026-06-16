"""
Shared risk band classification logic.

Scores align to 10-point checklist items (0, 10, 20, … 100). Bands use
decade boundaries so labels match achievable scores: 0-30, 40-60, 70-100.
"""
from app.models.scoring import RiskBand

AT_RISK_MAX_SCORE = 30
GOOD_MIN_SCORE = 40
GOOD_MAX_SCORE = 60
EXCELLENT_MIN_SCORE = 70

# Backward-compatible aliases used by manager dashboard queries.
HEALTHY_MIN_SCORE = EXCELLENT_MIN_SCORE


def get_risk_band(score: float) -> RiskBand:
    """
    Classify score into risk band.

    Rules:
    - 0-30: at risk (red)
    - 40-60: good (yellow)
    - 70-100: excellent (green)

    Scores in 31-39 or 61-69 (e.g. from partial item counts) map conservatively:
    below 40 stays at risk; 40-69 below excellent stays good.
    """
    if score <= AT_RISK_MAX_SCORE:
        return RiskBand.RED
    if score >= EXCELLENT_MIN_SCORE:
        return RiskBand.GREEN
    if score >= GOOD_MIN_SCORE:
        return RiskBand.YELLOW
    return RiskBand.RED


def get_risk_label(risk_band: RiskBand | str) -> str:
    """Human-readable label for risk band."""
    value = risk_band.value if hasattr(risk_band, "value") else risk_band
    labels = {
        "green": "Excellent",
        "yellow": "Good",
        "red": "At Risk",
    }
    return labels.get(value, "Unknown")
