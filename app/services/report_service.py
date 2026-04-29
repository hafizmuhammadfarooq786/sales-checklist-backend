"""
Report generation: two-page Sales Checklist PDF (ReportLab).
Page 1: header + checklist (Item / Yes-No / Definition) + raw score explanation.
Page 2: same header + item notes (no score block).
"""
import os
import re
import tempfile
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from xml.sax.saxutils import escape

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import HRFlowable, Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.core.config import settings
from app.models.session import Session
from app.services.s3_service import get_s3_service

# Bundled default when org logo is missing or fails to load
_DEFAULT_LOGO_PATH = (
    Path(__file__).resolve().parent.parent / "static" / "branding" / "default_sales_checklist_logo.png"
)

NAVY = colors.HexColor("#1a365d")
HEADER_TEXT = colors.white
GRID = colors.HexColor("#c8d0e0")


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


async def _fetch_org_logo_bytes(url: str) -> Optional[bytes]:
    u = (url or "").strip()
    if not u:
        return None
    try:
        async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
            r = await client.get(u)
            if r.status_code != 200:
                return None
            content = r.content
            if not content or len(content) < 32:
                return None
            ctype = (r.headers.get("content-type") or "").lower()
            if ctype and not any(x in ctype for x in ("image", "octet-stream", "application/x-www-form-urlencoded")):
                if "html" in ctype or "json" in ctype:
                    return None
            return content
    except Exception:
        return None


async def _resolve_logo_bytes(organization_logo_url: Optional[str]) -> bytes:
    if organization_logo_url:
        data = await _fetch_org_logo_bytes(organization_logo_url)
        if data:
            return data
    return _load_default_logo_bytes()


def _logo_flowable(logo_bytes: bytes, max_width: float = 0.7 * inch) -> Image:
    bio = BytesIO(logo_bytes)
    img = Image(bio)
    iw, ih = img.imageWidth, img.imageHeight
    if iw <= 0 or ih <= 0:
        iw, ih = 512, 512
    scale = max_width / float(iw)
    img.drawWidth = max_width
    img.drawHeight = ih * scale
    return img


class ReportService:
    """Two-page checklist PDF for sessions."""

    def __init__(self) -> None:
        self.styles = getSampleStyleSheet()
        self._cell_body = _para_style(
            "ChecklistCellBody",
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#1a1a1a"),
        )
        self._cell_header = _para_style(
            "ChecklistCellHeader",
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=11,
            textColor=HEADER_TEXT,
            alignment=1,
        )
        self._header_meta = _para_style(
            "HeaderMeta",
            fontName="Helvetica",
            fontSize=10,
            leading=13,
            textColor=colors.HexColor("#1a1a1a"),
            alignment=0,
        )
        self._header_meta_label = ParagraphStyle(
            "HeaderMetaLabel",
            parent=self.styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
            textColor=NAVY,
            alignment=2,
        )
        self._score_blurb = _para_style(
            "ScoreBlurb",
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#333333"),
        )
        self._page_title = _para_style(
            "PageTitle",
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=NAVY,
            alignment=0,
        )
        self._notes_label = _para_style(
            "NotesLabel",
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#223b66"),
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

        def _draw_page_border(canvas, _doc):
            # User-requested: page border only (no header boxes),
            # drawn on both pages at a "2px-ish" thickness.
            w, h = letter
            # Match ReportLab content margins for alignment with tables/text.
            inset = 0.5 * inch
            canvas.saveState()
            canvas.setStrokeColor(colors.HexColor("#111827"))  # slate-900-ish
            canvas.setLineWidth(1.2)  # thin ~2px-ish
            canvas.rect(inset, inset, w - inset * 2, h - inset * 2, stroke=1, fill=0)
            canvas.restoreState()

        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=0.5 * inch,
            leftMargin=0.5 * inch,
            topMargin=0.5 * inch,
            bottomMargin=0.5 * inch,
            title=pdf_title,
            author="The Sales Checklist",
            onFirstPage=_draw_page_border,
            onLaterPages=_draw_page_border,
        )

        story: List[Any] = []
        story.extend(
            self._build_shared_header(_logo_flowable(logo_bytes), customer, str(pursuit), review_str)
        )
        story.append(Spacer(1, 10))
        story.append(Paragraph("Checklist", self._page_title))
        story.append(Spacer(1, 4))

        if responses_data:
            story.extend(self._build_page1_checklist_table(responses_data))
        else:
            story.append(Paragraph("No checklist responses.", self._cell_body))

        story.append(Spacer(1, 10))
        story.extend(self._build_score_explanation(raw_total, int(max_raw)))

        story.append(PageBreak())
        story.extend(
            self._build_shared_header(_logo_flowable(logo_bytes), customer, str(pursuit), review_str)
        )
        story.append(Spacer(1, 10))
        story.append(Paragraph("Checklist item notes", self._page_title))
        story.append(Spacer(1, 4))
        if responses_data:
            story.extend(self._build_page2_notes_table(responses_data, notes_by_item_id))
        else:
            story.append(Paragraph("No notes.", self._cell_body))

        story.append(Spacer(1, 16))
        story.extend(self._build_footer())

        doc.build(story)

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
        """Normalize enum-like values to uppercase label only."""
        raw = str(pursuit or "").strip()
        if not raw:
            return "N/A"
        if "." in raw:
            raw = raw.split(".")[-1]
        return raw.upper().replace(" ", "_")

    def _build_shared_header(
        self,
        logo: Image,
        customer: str,
        pursuit: str,
        review_date: str,
    ) -> List[Any]:
        meta_rows = [
            [
                Paragraph("<b>Customer</b>", self._header_meta_label),
                _safe_paragraph_html(customer, self._header_meta),
            ],
            [
                Paragraph("<b>Deal Stage</b>", self._header_meta_label),
                _safe_paragraph_html(pursuit, self._header_meta),
            ],
            [
                Paragraph("<b>Review date</b>", self._header_meta_label),
                _safe_paragraph_html(review_date, self._header_meta),
            ],
        ]
        meta_table = Table(meta_rows, colWidths=[1.15 * inch, 4.35 * inch])
        meta_table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ALIGN", (0, 0), (0, -1), "RIGHT"),
                    ("ALIGN", (1, 0), (1, -1), "LEFT"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                ]
            )
        )

        outer = Table(
            [[logo, meta_table]],
            colWidths=[1.35 * inch, 5.65 * inch],
        )
        outer.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        return [outer, Spacer(1, 6)]

    def _build_page1_checklist_table(self, responses_data: List[Dict[str, Any]]) -> List[Any]:
        header = [
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
            if validated is True:
                yn = "Yes"
            elif validated is False:
                yn = "No"
            else:
                yn = "—"
            rows.append(
                [
                    _safe_paragraph_html(str(title), self._cell_body),
                    Paragraph(f"<para align='center'>{escape(yn)}</para>", self._cell_body),
                    _safe_paragraph_html(str(definition), self._cell_body),
                ]
            )

        tbl = Table(
            rows,
            colWidths=[1.35 * inch, 0.45 * inch, 5.2 * inch],
            repeatRows=1,
        )
        tbl.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                    ("TEXTCOLOR", (0, 0), (-1, 0), HEADER_TEXT),
                    ("GRID", (0, 0), (-1, -1), 0.5, GRID),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7f8fb")]),
                ]
            )
        )
        return [tbl]

    def _build_score_explanation(self, raw_total: int, max_raw: int) -> List[Any]:
        lines = (
            "Each checklist item is scored as follows: "
            "<b>Yes</b> counts as <b>10</b> points; <b>No</b> counts as <b>0</b> points. "
            "The <b>total score</b> is the sum of those item scores."
        )
        total_line = (
            f"<b>Total score for this checklist:</b> {int(raw_total)} "
            f"out of {int(max_raw)}."
        )
        return [
            Paragraph(lines, self._score_blurb),
            Spacer(1, 4),
            Paragraph(total_line, self._score_blurb),
        ]

    def _build_page2_notes_table(
        self,
        responses_data: List[Dict[str, Any]],
        notes_by_item_id: Dict[int, Dict[str, Any]],
    ) -> List[Any]:
        header = [
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
            title = item.get("title") or item.get("name") or f"Item {iid}"
            note_payload = notes_by_item_id.get(iid, {}) if iid is not None else {}
            rows.append(
                [
                    _safe_paragraph_html(str(title), self._cell_body),
                    self._build_notes_cell(note_payload),
                ]
            )
        tbl = Table(rows, colWidths=[1.85 * inch, 5.15 * inch], repeatRows=1)
        tbl.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                    ("TEXTCOLOR", (0, 0), (-1, 0), HEADER_TEXT),
                    ("GRID", (0, 0), (-1, -1), 0.5, GRID),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7f8fb")]),
                ]
            )
        )
        return [tbl]

    def _build_notes_cell(self, payload: Dict[str, Any]) -> Any:
        """
        Build rich notes cell content:
        - Note text paragraph
        - Decision influencers mini-table
        - Structured content sections with compact tables
        """
        if not payload:
            return _safe_paragraph_html("", self._cell_body)

        blocks: List[Any] = []
        note_text = (payload.get("note_text") or "").strip()
        influencers = payload.get("decision_influencers") or []
        structured = payload.get("structured_content")

        if note_text:
            blocks.append(_safe_paragraph_html(note_text, self._cell_body))

        if influencers:
            if blocks:
                blocks.append(Spacer(1, 3))
            blocks.append(Paragraph("Decision influencers", self._notes_label))
            blocks.append(Spacer(1, 2))
            blocks.append(self._build_influencers_table(influencers))

        if structured:
            if blocks:
                blocks.append(Spacer(1, 3))
            blocks.append(Paragraph("Structured notes", self._notes_label))
            blocks.append(Spacer(1, 2))
            blocks.extend(self._build_structured_blocks(structured))

        return blocks if blocks else _safe_paragraph_html("", self._cell_body)

    def _build_influencers_table(self, influencers: List[Dict[str, Any]]) -> Table:
        rows: List[List[Any]] = [
            [
                Paragraph("<b>Name</b>", self._cell_body),
                Paragraph("<b>Title</b>", self._cell_body),
                Paragraph("<b>Email</b>", self._cell_body),
            ]
        ]
        for inf in influencers:
            rows.append(
                [
                    _safe_paragraph_html(str(inf.get("name") or ""), self._cell_body),
                    _safe_paragraph_html(str(inf.get("title") or ""), self._cell_body),
                    _safe_paragraph_html(str(inf.get("email") or ""), self._cell_body),
                ]
            )
        tbl = Table(rows, colWidths=[1.0 * inch, 1.25 * inch, 2.7 * inch], repeatRows=1)
        tbl.setStyle(
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
        return tbl

    def _build_structured_blocks(self, data: Any) -> List[Any]:
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
                            _safe_paragraph_html(str(k).replace("_", " ").title(), self._cell_body),
                            _safe_paragraph_html("" if v is None else str(v), self._cell_body),
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
                rows: List[List[Any]] = [[Paragraph(f"<b>{h}</b>", self._cell_body) for h in headers]]
                for d in data:
                    rows.append(
                        [
                            _safe_paragraph_html(str(d.get(h) or ""), self._cell_body)
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
                    [Paragraph("<b>#</b>", self._cell_body), Paragraph("<b>Value</b>", self._cell_body)]
                ]
                for idx, item in enumerate(data, start=1):
                    rows.append(
                        [
                            _safe_paragraph_html(str(idx), self._cell_body),
                            _safe_paragraph_html(str(item), self._cell_body),
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
            return [_safe_paragraph_html(str(data), self._cell_body)]

        return [_safe_paragraph_html(str(data), self._cell_body)]

    def _try_build_role_name_result_table(self, structured: Dict[str, Any]) -> Optional[Table]:
        """
        Build a single 'ROLE | NAME | RESULT' table for the known structured schema
        used by Decision Influencers structured notes (Utilizer/Finalizer/Specifiers).
        """
        # Match the frontend visual order.
        role_keys = ["Finalizer", "Utilizer", "Specifiers"]
        found_any = False
        rows: List[List[Any]] = [
            [
                Paragraph("<b>ROLE</b>", self._cell_body),
                Paragraph("<b>NAME</b>", self._cell_body),
                Paragraph("<b>RESULT</b>", self._cell_body),
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
            name_cell = _safe_paragraph_html("\n".join(name_vals), self._cell_body)
            result_cell = _safe_paragraph_html("\n".join(result_vals), self._cell_body)
            rows.append([_safe_paragraph_html(role_label, self._cell_body), name_cell, result_cell])

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

    def _build_footer(self) -> List[Any]:
        foot = ParagraphStyle(
            "PdfFooter",
            parent=self.styles["Normal"],
            fontSize=7,
            textColor=colors.HexColor("#888888"),
            alignment=1,
        )
        return [
            HRFlowable(width="100%", thickness=0.5, color=GRID),
            Spacer(1, 6),
            Paragraph(
                f"The Sales Checklist™ | Generated {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
                foot,
            ),
        ]


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
