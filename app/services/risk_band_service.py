"""
Shared risk band classification logic.
"""
from app.models.scoring import RiskBand


HEALTHY_MIN_SCORE = 70
GOOD_PERFORMANCE_MIN_SCORE = 50


def get_risk_band(score: float) -> RiskBand:
    """
    Classify score into risk band.

    Rules:
    - 70 and above: healthy (green)
    - 50 to 69: good performance (yellow)
    - below 50: at risk (red)
    """
    if score >= HEALTHY_MIN_SCORE:
        return RiskBand.GREEN
    if score >= GOOD_PERFORMANCE_MIN_SCORE:
        return RiskBand.YELLOW
    return RiskBand.RED


def get_risk_label(risk_band: RiskBand | str) -> str:
    """
    Human-readable label for risk band.
    """
    value = risk_band.value if hasattr(risk_band, "value") else risk_band
    labels = {
        "green": "Healthy",
        "yellow": "Good Performance",
        "red": "At Risk",
    }
    return labels.get(value, "Unknown")
