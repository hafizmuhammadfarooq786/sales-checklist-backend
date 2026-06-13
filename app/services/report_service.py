"""
Report generation: strict two-page Sales Checklist PDF (ReportLab).
Page 1: header + checklist + score. Page 2: header + notes only.
Compact Inter typography; no checklist rows split onto page 2.
"""
import os
import re
import tempfile
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from xml.sax.saxutils import escape

from sqlalchemy.ext.asyncio import AsyncSession

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.core.config import settings
from app.models.session import Session
from app.services.checklist_pdf_icons import (
    build_definition_flowable,
    build_item_text_flowable,
    build_status_icon_flowable,
    build_yn_text_flowable,
)
from app.services.pdf_fonts import register_pdf_fonts
from app.services.risk_band_service import get_risk_label
from app.services.s3_service import get_s3_service

# Bundled default when org logo is missing or fails to load
_DEFAULT_LOGO_PATH = (
    Path(__file__).resolve().parent.parent / "static" / "branding" / "default_sales_checklist_logo.png"
)

NAVY = colors.HexColor("#0b2e59")
HEADER_TEXT = colors.white
GRID = colors.HexColor("#d7dce3")
ROW_SURFACE = colors.HexColor("#ffffff")
ROW_ALT = colors.HexColor("#f5f6f8")
SCORE_BOX_BG = colors.HexColor("#f5f6f8")
INK_MUTED = colors.HexColor("#5b6473")
FOOTER_TEXT = colors.HexColor("#888888")
STRONG = colors.HexColor("#198754")
CRITICAL = colors.HexColor("#b91c1c")

_DEAL_STAGE_LABELS = {
    "active": "Active",
    "prospect": "Prospect",
    "qualified": "Qualified",
    "proposal": "Proposal",
    "negotiation": "Negotiation",
    "won": "Won",
    "lost": "Lost",
    "no_decision": "No Decision",
    "disengaged": "Disengaged",
    "on_hold": "On Hold",
}

_RISK_BAND_COLORS = {
    "green": (colors.HexColor("#eaf7f0"), colors.HexColor("#198754")),
    "yellow": (colors.HexColor("#fff4e5"), colors.HexColor("#b45309")),
    "red": (colors.HexColor("#fdecec"), colors.HexColor("#b91c1c")),
}

# Keep page 2 to a single sheet when note text runs long
_MAX_NOTE_TEXT_CHARS = 320


def _truncate_note_text(text: str) -> str:
    cleaned = (text or "").strip()
    if len(cleaned) <= _MAX_NOTE_TEXT_CHARS:
        return cleaned
    return cleaned[:_MAX_NOTE_TEXT_CHARS].rstrip() + "…"


def _draw_page_footer(
    cnv: canvas.Canvas,
    page_num: int,
    page_count: int,
    footer_meta: Dict[str, Any],
) -> None:
    """Footer line, branding, and page numbers on every page."""
    w, _h = letter
    inset = 0.5 * inch
    font_name = footer_meta.get("font_regular", "Helvetica")
    generated_at = footer_meta.get("generated_at", "")

    cnv.saveState()
    line_y = 0.42 * inch
    cnv.setFont(font_name, 7)
    cnv.setFillColor(FOOTER_TEXT)
    left = f"The Sales Checklist™ | Generated {generated_at}"
    cnv.drawString(inset, line_y, left)

    page_label = f"Page {page_num} of {page_count}"
    cnv.drawCentredString(w / 2, line_y, page_label)
    cnv.restoreState()


class _NumberedCanvas(canvas.Canvas):
    """Two-pass canvas so footers can show 'Page X of Y'."""

    def __init__(self, *args, footer_meta: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states: List[Dict[str, Any]] = []
        self._footer_meta = footer_meta or {}

    def showPage(self) -> None:
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self) -> None:
        page_count = len(self._saved_page_states)
        for page_num, state in enumerate(self._saved_page_states, start=1):
            self.__dict__.update(state)
            _draw_page_footer(self, page_num, page_count, self._footer_meta)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)


def _para_style(name: str, **kwargs) -> ParagraphStyle:
    base = getSampleStyleSheet()["Normal"]
    return ParagraphStyle(name, parent=base, **kwargs)


def _safe_paragraph_html(text: str, style: ParagraphStyle) -> Paragraph:
    if not text:
        return Paragraph("", style)
    esc = escape(str(text))
    esc = esc.replace("\n", "<br/>")
    return Paragraph(esc, style)


def _load_default_logo_bytes() -> bytes:
    if not _DEFAULT_LOGO_PATH.is_file():
        raise FileNotFoundError(
            f"Default Sales Checklist logo not found at {_DEFAULT_LOGO_PATH}. "
            "Add default_sales_checklist_logo.png under app/static/branding/."
        )
    return _DEFAULT_LOGO_PATH.read_bytes()


async def _resolve_logo_bytes(organization_logo_url: Optional[str]) -> bytes:
    if organization_logo_url:
        from app.services.org_logo_service import load_organization_logo_bytes

        data = await load_organization_logo_bytes(organization_logo_url)
        if data:
            return data
    return _load_default_logo_bytes()


# Header logo — max height ~1in; width scales proportionally (wide logos need width cap, not height cap)
_MAX_LOGO_HEIGHT = 72
_MAX_LOGO_WIDTH = 4.0 * inch


def _logo_flowable(
    logo_bytes: bytes,
    max_height: float = _MAX_LOGO_HEIGHT,
    max_width: float = _MAX_LOGO_WIDTH,
) -> Image:
    bio = BytesIO(logo_bytes)
    img = Image(bio)
    iw, ih = img.imageWidth, img.imageHeight
    if iw <= 0 or ih <= 0:
        iw, ih = 512, 512
    scale = min(max_height / float(ih), max_width / float(iw))
    img.drawWidth = iw * scale
    img.drawHeight = ih * scale
    return img


class ReportService:
    """Two-page checklist PDF for sessions."""

    def __init__(self) -> None:
        self.styles = getSampleStyleSheet()
        font_regular, font_bold = register_pdf_fonts()
        self._font_regular = font_regular
        self._font_bold = font_bold

        self._cell_body = _para_style(
            "ChecklistCellBody",
            fontName=font_regular,
            fontSize=6.5,
            leading=8,
            textColor=colors.HexColor("#1a1a1a"),
        )
        self._cell_header = _para_style(
            "ChecklistCellHeader",
            fontName=font_bold,
            fontSize=7,
            leading=8,
            textColor=HEADER_TEXT,
            alignment=1,
        )
        self._header_meta = _para_style(
            "HeaderMeta",
            fontName=font_regular,
            fontSize=10,
            leading=13,
            textColor=colors.HexColor("#1a1a1a"),
            alignment=0,
        )
        self._header_meta_label = ParagraphStyle(
            "HeaderMetaLabel",
            parent=self.styles["Normal"],
            fontName=font_bold,
            fontSize=9,
            leading=12,
            textColor=NAVY,
            alignment=2,
        )
        self._header_meta_label_center = ParagraphStyle(
            "HeaderMetaLabelCenter",
            parent=self.styles["Normal"],
            fontName=font_bold,
            fontSize=7,
            leading=9,
            textColor=NAVY,
            alignment=1,
        )
        self._header_meta_center = _para_style(
            "HeaderMetaCenter",
            fontName=font_regular,
            fontSize=7.5,
            leading=9,
            textColor=colors.HexColor("#1a1a1a"),
            alignment=1,
        )
        self._org_name = _para_style(
            "OrgName",
            fontName=font_bold,
            fontSize=9,
            leading=11,
            textColor=NAVY,
            alignment=1,
        )
        self._score_blurb = _para_style(
            "ScoreBlurb",
            fontName=font_regular,
            fontSize=6.5,
            leading=8,
            textColor=colors.HexColor("#333333"),
        )
        self._score_value = _para_style(
            "ScoreValue",
            fontName=font_bold,
            fontSize=14,
            leading=16,
            textColor=NAVY,
            alignment=1,
        )
        self._score_sub = _para_style(
            "ScoreSub",
            fontName=font_regular,
            fontSize=6,
            leading=7,
            textColor=INK_MUTED,
            alignment=1,
        )
        self._score_chip = _para_style(
            "ScoreChip",
            fontName=font_bold,
            fontSize=6.5,
            leading=8,
            alignment=1,
        )
        self._page_title = _para_style(
            "PageTitle",
            fontName=font_bold,
            fontSize=11,
            leading=14,
            textColor=NAVY,
            alignment=0,
        )
        self._notes_label = _para_style(
            "NotesLabel",
            fontName=font_bold,
            fontSize=6.5,
            leading=8,
            textColor=colors.HexColor("#223b66"),
        )
        self._notes_body = _para_style(
            "NotesBody",
            fontName=font_regular,
            fontSize=6.5,
            leading=8,
            textColor=colors.HexColor("#1a1a1a"),
        )
        self._item_title = _para_style(
            "ItemTitle",
            fontName=font_bold,
            fontSize=6.5,
            leading=8,
            textColor=colors.HexColor("#0b1220"),
        )
        self._index_cell = _para_style(
            "IndexCell",
            fontName=font_bold,
            fontSize=6.5,
            leading=8,
            textColor=colors.HexColor("#0b1220"),
            alignment=1,
        )
        self._yn_yes = _para_style(
            "YnYes",
            fontName=font_bold,
            fontSize=6.5,
            leading=8,
            textColor=STRONG,
            alignment=1,
        )
        self._yn_no = _para_style(
            "YnNo",
            fontName=font_bold,
            fontSize=6.5,
            leading=8,
            textColor=CRITICAL,
            alignment=1,
        )
        self._yn_neutral = _para_style(
            "YnNeutral",
            fontName=font_regular,
            fontSize=6.5,
            leading=8,
            textColor=INK_MUTED,
            alignment=1,
        )
        self._definition_letter = _para_style(
            "DefinitionLetter",
            fontName=font_bold,
            fontSize=6.5,
            leading=8,
            textColor=colors.HexColor("#0b1220"),
        )

    async def generate_session_report(
        self,
        session_id: int,
        user_id: int,
        session_data: Dict[str, Any],
        scoring_data: Dict[str, Any],
        coaching_data: Optional[Dict[str, Any]] = None,
        responses_data: Optional[List[Dict[str, Any]]] = None,
        organization_logo_url: Optional[str] = None,
        organization_name: Optional[str] = None,
        notes_by_item_id: Optional[Dict[int, str]] = None,
    ) -> Dict[str, Any]:
        """
        Build PDF and upload to S3 (or local fallback). coaching_data is ignored (legacy param).
        """
        del coaching_data  # not used in checklist PDF
        notes_by_item_id = notes_by_item_id or {}

        logo_bytes = await _resolve_logo_bytes(organization_logo_url)

        customer = session_data.get("customer_name") or "N/A"
        pursuit = session_data.get("deal_stage")
        if pursuit is not None and not isinstance(pursuit, str):
            pursuit = getattr(pursuit, "value", str(pursuit))
        pursuit = self._format_pursuit_label(pursuit or "N/A")
        review_dt = session_data.get("review_generated_at")
        if isinstance(review_dt, datetime):
            review_str = review_dt.strftime("%B %d, %Y")
        else:
            review_str = datetime.utcnow().strftime("%B %d, %Y")

        raw_total = scoring_data.get("raw_points_total")
        max_raw = scoring_data.get("max_raw_points")
        items_total = int(scoring_data.get("items_total") or 0)
        if max_raw is None:
            max_raw = items_total * 10
        if raw_total is None:
            validated = int(scoring_data.get("items_validated") or 0)
            raw_total = validated * 10

        buffer = BytesIO()
        customer_name = session_data.get("customer_name", "Report")
        pdf_title = f"The Sales Checklist — {customer_name}"
        generated_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        footer_meta = {
            "generated_at": generated_at,
            "font_regular": self._font_regular,
        }

        def _canvas_maker(filename: str, **kwargs):
            return _NumberedCanvas(filename, footer_meta=footer_meta, **kwargs)

        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=0.45 * inch,
            leftMargin=0.45 * inch,
            topMargin=0.42 * inch,
            bottomMargin=0.52 * inch,
            title=pdf_title,
            author="The Sales Checklist",
        )

        story: List[Any] = []
        org_display = (organization_name or "").strip() or "The Sales Checklist"
        page1: List[Any] = []
        page1.extend(
            self._build_shared_header(
                _logo_flowable(logo_bytes),
                org_display,
                customer,
                str(pursuit),
                review_str,
            )
        )
        if responses_data:
            page1.extend(self._build_page1_checklist_table(responses_data))
        else:
            page1.append(Paragraph("No checklist responses.", self._cell_body))
        page1.extend(self._build_score_explanation(scoring_data, raw_total, int(max_raw)))
        story.append(KeepTogether(page1))

        story.append(PageBreak())

        story.extend(
            self._build_shared_header(
                _logo_flowable(logo_bytes),
                org_display,
                customer,
                str(pursuit),
                review_str,
            )
        )
        if responses_data:
            story.extend(self._build_page2_notes_table(responses_data, notes_by_item_id))
        else:
            story.append(Paragraph("No notes.", self._notes_body))

        doc.build(story, canvasmaker=_canvas_maker)

        pdf_bytes = buffer.getvalue()
        buffer.close()
        file_size = len(pdf_bytes)

        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        temp_file.write(pdf_bytes)
        temp_file.close()

        sanitized_name = self._sanitize_filename(session_data.get("customer_name", ""))
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{sanitized_name}_{timestamp}.pdf"
        s3_key = f"reports/{user_id}/{session_id}/{filename}"

        try:
            s3_service = get_s3_service()
            s3_url = s3_service.upload_file(
                temp_file.name,
                s3_key,
                content_type="application/pdf",
                bucket_name=settings.S3_BUCKET_REPORTS,
            )
            storage_type = "s3"
        except Exception:
            local_dir = f"uploads/reports/{user_id}/{session_id}"
            os.makedirs(local_dir, exist_ok=True)
            local_path = f"{local_dir}/{filename}"
            import shutil

            shutil.copy(temp_file.name, local_path)
            s3_url = local_path
            storage_type = "local"
            s3_key = local_path
        finally:
            os.unlink(temp_file.name)

        return {
            "pdf_url": s3_url,
            "s3_bucket": settings.S3_BUCKET_REPORTS if storage_type == "s3" else None,
            "s3_key": s3_key if storage_type == "s3" else None,
            "file_size": file_size,
            "storage_type": storage_type,
            "generated_at": datetime.utcnow().isoformat(),
        }

    def _sanitize_filename(self, name: str) -> str:
        if not name:
            return "report"
        name = name.strip().replace(" ", "_")
        name = re.sub(r"[^a-zA-Z0-9_\-.]", "", name)
        name = re.sub(r"_+", "_", name)
        return name[:50] if name else "report"

    def _format_pursuit_label(self, pursuit: str) -> str:
        """Human-readable deal stage (matches frontend DEAL_STAGE_OPTIONS)."""
        raw = str(pursuit or "").strip()
        if not raw:
            return "N/A"
        if "." in raw:
            raw = raw.split(".")[-1]
        key = raw.lower().replace(" ", "_")
        if key in _DEAL_STAGE_LABELS:
            return _DEAL_STAGE_LABELS[key]
        return key.replace("_", " ").title()

    def _build_meta_field(self, label: str, value: str) -> Table:
        cell = Table(
            [
                [Paragraph(f"<b>{label}</b>", self._header_meta_label_center)],
                [_safe_paragraph_html(value, self._header_meta_center)],
            ],
            colWidths=[2.2 * inch],
        )
        cell.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ]
            )
        )
        return cell

    def _build_shared_header(
        self,
        logo: Image,
        organization_name: str,
        customer: str,
        pursuit: str,
        review_date: str,
    ) -> List[Any]:
        content_width = 7.0 * inch

        logo_row = Table([[logo]], colWidths=[content_width])
        logo_row.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ]
            )
        )

        org_row = Table(
            [[_safe_paragraph_html(organization_name, self._org_name)]],
            colWidths=[content_width],
        )
        org_row.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )

        meta_row = Table(
            [
                [
                    self._build_meta_field("Customer", customer),
                    self._build_meta_field("Deal Stage", pursuit),
                    self._build_meta_field("Review date", review_date),
                ]
            ],
            colWidths=[2.2 * inch, 2.2 * inch, 2.6 * inch],
        )
        meta_row.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ]
            )
        )

        header_stack = Table(
            [[logo_row], [org_row], [meta_row]],
            colWidths=[content_width],
        )
        header_stack.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ]
            )
        )
        return [header_stack, Spacer(1, 4)]

    def _table_border_style(self) -> list:
        """Shared grid-only borders for checklist/notes tables."""
        return [
            ("GRID", (0, 0), (-1, -1), 0.5, GRID),
            ("LINEBELOW", (0, 0), (-1, 0), 0.75, GRID),
        ]

    def _checklist_table_style(self) -> TableStyle:
        # Page 1: status icon | item title | Y/N text | definition
        return TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), HEADER_TEXT),
                *self._table_border_style(),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("VALIGN", (0, 1), (2, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (0, -1), "CENTER"),
                ("ALIGN", (2, 0), (2, -1), "CENTER"),
                ("ALIGN", (1, 0), (1, -1), "LEFT"),
                ("ALIGN", (3, 0), (3, -1), "LEFT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (0, -1), 2),
                ("RIGHTPADDING", (0, 0), (0, -1), 2),
                ("TOPPADDING", (0, 0), (-1, 0), 3),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 3),
                ("TOPPADDING", (0, 1), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 3),
                ("TOPPADDING", (0, 1), (2, -1), 4),
                ("BOTTOMPADDING", (0, 1), (2, -1), 4),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [ROW_SURFACE, ROW_ALT]),
            ]
        )

    def _build_page1_checklist_table(self, responses_data: List[Dict[str, Any]]) -> List[Any]:
        # tick/cross | title | Yes/No text | definition
        header = [
            Paragraph("<nobr>STATUS</nobr>", self._cell_header),
            Paragraph("ITEM", self._cell_header),
            Paragraph("Y/N", self._cell_header),
            Paragraph("DEFINITION", self._cell_header),
        ]
        rows: List[List[Any]] = [header]
        sorted_responses = sorted(
            responses_data,
            key=lambda r: r.get("item", {}).get("order", r.get("item_id", 0)),
        )
        for resp in sorted_responses:
            item = resp.get("item") or {}
            title = item.get("title") or item.get("name") or f"Item {resp.get('item_id', '')}"
            definition = item.get("definition") or ""
            validated = resp.get("is_validated")
            rows.append(
                [
                    build_status_icon_flowable(
                        validated, self._index_cell, size=0.13 * inch
                    ),
                    build_item_text_flowable(str(title), self._item_title),
                    build_yn_text_flowable(
                        validated,
                        self._yn_yes,
                        self._yn_no,
                        self._yn_neutral,
                    ),
                    build_definition_flowable(
                        str(definition),
                        self._cell_body,
                        self._definition_letter,
                    ),
                ]
            )

        tbl = Table(
            rows,
            colWidths=[0.60 * inch, 1.12 * inch, 0.32 * inch, 4.96 * inch],
            repeatRows=1,
            splitByRow=0,
        )
        tbl.setStyle(self._checklist_table_style())
        return [tbl]

    def _risk_band_chip(self, risk_band: Any) -> Table:
        value = risk_band.value if hasattr(risk_band, "value") else str(risk_band or "")
        bg, fg = _RISK_BAND_COLORS.get(value, (SCORE_BOX_BG, NAVY))
        label = get_risk_label(value)
        chip_style = ParagraphStyle(
            "RiskChipDynamic",
            parent=self._score_chip,
            textColor=fg,
        )
        chip = Table(
            [[Paragraph(f"<b>{escape(label)}</b>", chip_style)]],
            colWidths=[0.95 * inch],
        )
        chip.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), bg),
                    ("BOX", (0, 0), (-1, -1), 1, fg),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ]
            )
        )
        return chip

    def _build_score_explanation(
        self,
        scoring_data: Dict[str, Any],
        raw_total: int,
        max_raw: int,
    ) -> List[Any]:
        total_score = scoring_data.get("total_score")
        if total_score is None and max_raw > 0:
            total_score = (raw_total / max_raw) * 100
        score_pct = int(round(float(total_score or 0)))

        blurb = Paragraph(
            (
                "<b>Yes</b> = 10 pts, <b>No</b> = 0 pts. "
                f"Raw points: {int(raw_total)}/{int(max_raw)}."
            ),
            self._score_blurb,
        )

        score_line = Table(
            [
                [
                    Paragraph(f"<b>{score_pct}</b>", self._score_value),
                    Paragraph("/100", self._score_sub),
                ]
            ],
            colWidths=[0.5 * inch, 0.35 * inch],
        )
        score_line.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ]
            )
        )

        score_block = Table(
            [
                [score_line],
                [self._risk_band_chip(scoring_data.get("risk_band"))],
            ],
            colWidths=[1.45 * inch],
        )
        score_block.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (0, 0), 1),
                    ("TOPPADDING", (0, 1), (0, 1), 2),
                    ("BOTTOMPADDING", (0, 1), (0, 1), 0),
                ]
            )
        )

        inner = Table(
            [[blurb, score_block]],
            colWidths=[5.55 * inch, 1.45 * inch],
        )
        inner.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), SCORE_BOX_BG),
                    ("GRID", (0, 0), (-1, -1), 0.5, GRID),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ALIGN", (1, 0), (1, 0), "CENTER"),
                    ("LEFTPADDING", (0, 0), (0, 0), 6),
                    ("RIGHTPADDING", (0, 0), (0, 0), 4),
                    ("LEFTPADDING", (1, 0), (1, 0), 2),
                    ("RIGHTPADDING", (1, 0), (1, 0), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        return [Spacer(1, 3), inner]

    def _build_page2_notes_table(
        self,
        responses_data: List[Dict[str, Any]],
        notes_by_item_id: Dict[int, Dict[str, Any]],
    ) -> List[Any]:
        header = [
            Paragraph("#", self._cell_header),
            Paragraph("ITEM", self._cell_header),
            Paragraph("NOTES", self._cell_header),
        ]
        rows: List[List[Any]] = [header]
        sorted_responses = sorted(
            responses_data,
            key=lambda r: r.get("item", {}).get("order", r.get("item_id", 0)),
        )
        for resp in sorted_responses:
            item = resp.get("item") or {}
            iid = resp.get("item_id")
            order = int(item.get("order") or iid or 0)
            title = item.get("title") or item.get("name") or f"Item {iid}"
            note_payload = notes_by_item_id.get(iid, {}) if iid is not None else {}
            rows.append(
                [
                    Paragraph(str(order), self._index_cell),
                    build_item_text_flowable(str(title), self._item_title),
                    self._build_notes_cell(note_payload),
                ]
            )
        tbl = Table(
            rows,
            colWidths=[0.28 * inch, 1.2 * inch, 5.52 * inch],
            repeatRows=1,
            splitByRow=1,
        )
        notes_style = TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), HEADER_TEXT),
                *self._table_border_style(),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("VALIGN", (0, 1), (1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (0, -1), "CENTER"),
                ("ALIGN", (1, 0), (-1, -1), "LEFT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, 0), 3),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 3),
                ("TOPPADDING", (0, 1), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 3),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [ROW_SURFACE, ROW_ALT]),
            ]
        )
        tbl.setStyle(notes_style)
        return [tbl]

    def _build_notes_cell(self, payload: Dict[str, Any]) -> Any:
        """
        Build rich notes cell content:
        - Note text paragraph
        - Decision influencers mini-table
        - Structured content sections with compact tables
        """
        if not payload:
            return _safe_paragraph_html("", self._notes_body)

        blocks: List[Any] = []
        note_text = _truncate_note_text(payload.get("note_text") or "")
        influencers = payload.get("decision_influencers") or []
        structured = payload.get("structured_content")

        if note_text:
            blocks.append(_safe_paragraph_html(note_text, self._notes_body))

        if influencers:
            if blocks:
                blocks.append(Spacer(1, 1))
            blocks.append(Paragraph("Decision influencers", self._notes_label))
            blocks.append(Spacer(1, 1))
            blocks.append(self._build_influencers_table(influencers))

        if structured:
            if blocks:
                blocks.append(Spacer(1, 1))
            blocks.append(Paragraph("Structured notes", self._notes_label))
            blocks.append(Spacer(1, 1))
            blocks.extend(self._build_structured_blocks(structured))

        return blocks if blocks else _safe_paragraph_html("", self._notes_body)

    def _build_influencers_table(self, influencers: List[Dict[str, Any]]) -> Table:
        body = self._notes_body
        rows: List[List[Any]] = [
            [
                Paragraph("<b>Name</b>", body),
                Paragraph("<b>Title</b>", body),
                Paragraph("<b>Email</b>", body),
            ]
        ]
        for inf in influencers:
            rows.append(
                [
                    _safe_paragraph_html(str(inf.get("name") or ""), body),
                    _safe_paragraph_html(str(inf.get("title") or ""), body),
                    _safe_paragraph_html(str(inf.get("email") or ""), body),
                ]
            )
        tbl = Table(rows, colWidths=[1.0 * inch, 1.25 * inch, 2.7 * inch], repeatRows=1)
        tbl.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.35, GRID),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef2f9")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 2),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                    ("TOPPADDING", (0, 0), (-1, -1), 1),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                ]
            )
        )
        return tbl

    def _build_structured_blocks(self, data: Any) -> List[Any]:
        body = self._notes_body
        blocks: List[Any] = []
        if isinstance(data, dict):
            role_table = self._try_build_role_name_result_table(data)
            if role_table is not None:
                return [role_table]

            # Render scalar key-values first
            scalar_pairs = [(k, v) for k, v in data.items() if not isinstance(v, (dict, list))]
            if scalar_pairs:
                # Scalar key/value pairs: render as a compact 2-column table (no header),
                # so it matches the frontend "table JSONs" style better.
                rows: List[List[Any]] = []
                for k, v in scalar_pairs:
                    rows.append(
                        [
                            _safe_paragraph_html(str(k).replace("_", " ").title(), body),
                            _safe_paragraph_html("" if v is None else str(v), body),
                        ]
                    )
                kv_table = Table(rows, colWidths=[1.05 * inch, 3.65 * inch], repeatRows=0)
                kv_table.setStyle(
                    TableStyle(
                        [
                            ("GRID", (0, 0), (-1, -1), 0.35, GRID),
                            ("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("LEFTPADDING", (0, 0), (-1, -1), 3),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                            ("TOPPADDING", (0, 0), (-1, -1), 2),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                        ]
                    )
                )
                blocks.append(kv_table)

            for key, val in data.items():
                if isinstance(val, (dict, list)):
                    if blocks:
                        blocks.append(Spacer(1, 2))
                    blocks.append(Paragraph(str(key).replace("_", " ").title(), self._notes_label))
                    blocks.append(Spacer(1, 1))
                    blocks.extend(self._build_structured_blocks(val))
            return blocks

        if isinstance(data, list):
            if all(isinstance(x, dict) for x in data):
                headers = []
                for d in data:
                    for k in d.keys():
                        if k not in headers:
                            headers.append(k)
                rows: List[List[Any]] = [[Paragraph(f"<b>{h}</b>", body) for h in headers]]
                for d in data:
                    rows.append(
                        [
                            _safe_paragraph_html(str(d.get(h) or ""), body)
                            for h in headers
                        ]
                    )
                total_width = 4.7 * inch
                col_width = total_width / max(len(headers), 1)
                t = Table(
                    rows,
                    colWidths=[col_width] * max(len(headers), 1),
                    repeatRows=1,
                )
                t.setStyle(
                    TableStyle(
                        [
                            ("GRID", (0, 0), (-1, -1), 0.35, GRID),
                            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef2f9")),
                            ("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("LEFTPADDING", (0, 0), (-1, -1), 3),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                            ("TOPPADDING", (0, 0), (-1, -1), 2),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                        ]
                    )
                )
                return [t]

            if all(not isinstance(x, (dict, list)) for x in data):
                rows = [
                    [Paragraph("<b>#</b>", body), Paragraph("<b>Value</b>", body)]
                ]
                for idx, item in enumerate(data, start=1):
                    rows.append(
                        [
                            _safe_paragraph_html(str(idx), body),
                            _safe_paragraph_html(str(item), body),
                        ]
                    )
                t = Table(rows, colWidths=[0.35 * inch, 4.6 * inch], repeatRows=1)
                t.setStyle(
                    TableStyle(
                        [
                            ("GRID", (0, 0), (-1, -1), 0.35, GRID),
                            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef2f9")),
                            ("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("LEFTPADDING", (0, 0), (-1, -1), 3),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                            ("TOPPADDING", (0, 0), (-1, -1), 2),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                        ]
                    )
                )
                return [t]

            # Mixed list fallback
            return [_safe_paragraph_html(str(data), body)]

        return [_safe_paragraph_html(str(data), body)]

    def _try_build_role_name_result_table(self, structured: Dict[str, Any]) -> Optional[Table]:
        """
        Build a single 'ROLE | NAME | RESULT' table for the known structured schema
        used by Decision Influencers structured notes (Utilizer/Finalizer/Specifiers).
        """
        # Match the frontend visual order.
        role_keys = ["Finalizer", "Utilizer", "Specifiers"]
        found_any = False
        body = self._notes_body
        rows: List[List[Any]] = [
            [
                Paragraph("<b>ROLE</b>", body),
                Paragraph("<b>NAME</b>", body),
                Paragraph("<b>RESULT</b>", body),
            ]
        ]

        for role in role_keys:
            role_payload = None
            # match key case-insensitively
            for k, v in structured.items():
                if str(k).strip().lower() == role.lower():
                    role_payload = v
                    break
            if not isinstance(role_payload, dict):
                continue

            # Results key is usually stable.
            results = None
            for k, v in role_payload.items():
                if str(k).strip().lower() in {"results", "result"}:
                    results = v
                    break
            if results is None:
                # Fallback (older/variant shapes)
                results = role_payload.get("Results") or role_payload.get("results") or role_payload.get("Result")

            # Names key can vary (sometimes it's actually a domain label like "Wifim").
            # First try common keys, then fall back to the first list-ish value that is not results.
            names = (
                role_payload.get("Names")
                or role_payload.get("names")
                or role_payload.get("Name")
                or role_payload.get("name")
            )
            if names is None:
                for k, v in role_payload.items():
                    if str(k).strip().lower() in {"results", "result"}:
                        continue
                    # Heuristic: any list/dict value might represent "Names".
                    if isinstance(v, (list, dict)):
                        names = v
                        break

            name_vals = self._normalize_structured_values(names)
            result_vals = self._normalize_structured_values(results)
            if name_vals or result_vals:
                found_any = True

            if not (name_vals and result_vals):
                continue

            role_label = role
            name_cell = _safe_paragraph_html("\n".join(name_vals), body)
            result_cell = _safe_paragraph_html("\n".join(result_vals), body)
            rows.append([_safe_paragraph_html(role_label, body), name_cell, result_cell])

        if not found_any or len(rows) <= 1:
            return None

        # Keep this within NOTES column width (~5.15in) to avoid overflow.
        tbl = Table(rows, colWidths=[0.85 * inch, 2.15 * inch, 1.85 * inch], repeatRows=1)
        tbl.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3f4f6")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#111827")),
                    ("GRID", (0, 0), (-1, -1), 0.35, GRID),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 3),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ]
            )
        )
        return tbl

    def _normalize_structured_values(self, v: Any) -> List[str]:
        if v is None:
            return []
        if isinstance(v, str):
            s = v.strip()
            return [s] if s else []
        if isinstance(v, (int, float, bool)):
            return [str(v)]
        if isinstance(v, list):
            out: List[str] = []
            for item in v:
                if item is None:
                    continue
                if isinstance(item, str):
                    s = item.strip()
                    if s:
                        out.append(s)
                    continue
                if isinstance(item, dict):
                    if "Value" in item and item["Value"] is not None:
                        s = str(item["Value"]).strip()
                        if s:
                            out.append(s)
                        continue
                    if "value" in item and item["value"] is not None:
                        s = str(item["value"]).strip()
                        if s:
                            out.append(s)
                        continue
                    # fallback: stringified dict
                    out.append(str(item))
                    continue
                out.append(str(item))
            return out
        if isinstance(v, dict):
            if "Value" in v and v["Value"] is not None:
                return [str(v["Value"]).strip()]
            if "value" in v and v["value"] is not None:
                return [str(v["value"]).strip()]
        return [str(v)]

_report_service: Optional[ReportService] = None


def get_report_service() -> ReportService:
    global _report_service
    if _report_service is None:
        _report_service = ReportService()
    return _report_service


def _extract_note_payload(note: Union[Any, Dict[str, Any]]) -> Dict[str, Any]:
    if note is None:
        return {}
    if isinstance(note, dict):
        return {
            "note_text": note.get("note_text"),
            "decision_influencers": note.get("decision_influencers") or [],
            "structured_content": note.get("structured_content"),
        }
    return {
        "note_text": getattr(note, "note_text", None),
        "decision_influencers": getattr(note, "decision_influencers", None) or [],
        "structured_content": getattr(note, "structured_content", None),
    }


async def build_notes_map_for_pdf(db: AsyncSession, session: Session) -> Dict[int, Dict[str, Any]]:
    """Latest active notes per checklist item for session opportunity (same keying as Notes API)."""
    from app.services.notes_service import bundle_latest_for_session, compute_opportunity_key

    key = compute_opportunity_key(
        session.customer_name,
        session.opportunity_name or "",
    )
    bundle = await bundle_latest_for_session(db, session, key)
    out: Dict[int, Dict[str, Any]] = {}
    for slot in bundle.items:
        if slot.note is None:
            out[slot.checklist_item_id] = {}
        else:
            out[slot.checklist_item_id] = _extract_note_payload(slot.note)
    return out
