"""Register Inter fonts for ReportLab PDF generation (falls back to Helvetica)."""
from pathlib import Path

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

_FONTS_DIR = Path(__file__).resolve().parent.parent / "static" / "fonts"

INTER_REGULAR = "Inter"
INTER_BOLD = "Inter-Bold"
FALLBACK_REGULAR = "Helvetica"
FALLBACK_BOLD = "Helvetica-Bold"

_registered = False
_active_regular = FALLBACK_REGULAR
_active_bold = FALLBACK_BOLD


def register_pdf_fonts() -> tuple[str, str]:
    """Register bundled Inter TTF files; return (regular_name, bold_name) for ParagraphStyle."""
    global _registered, _active_regular, _active_bold
    if _registered:
        return _active_regular, _active_bold

    regular_path = _FONTS_DIR / "Inter-Regular.ttf"
    bold_path = _FONTS_DIR / "Inter-Bold.ttf"
    try:
        if regular_path.is_file():
            pdfmetrics.registerFont(TTFont(INTER_REGULAR, str(regular_path)))
            _active_regular = INTER_REGULAR
        if bold_path.is_file():
            pdfmetrics.registerFont(TTFont(INTER_BOLD, str(bold_path)))
            _active_bold = INTER_BOLD
    except Exception:
        _active_regular = FALLBACK_REGULAR
        _active_bold = FALLBACK_BOLD

    _registered = True
    return _active_regular, _active_bold
