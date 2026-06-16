"""
Checklist item icons and definition formatting for PDF export.
Mirrors frontend `checklist-item-icon.ts` and `parse-definition.ts`.
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import Flowable, Paragraph, Table, TableStyle
from svglib.svglib import svg2rlg

_ICONS_DIR = Path(__file__).resolve().parent.parent / "static" / "checklist-icons"

ICON_BG = {
    "intel": colors.HexColor("#e5f1fd"),
    "warn": colors.HexColor("#fff4e5"),
    "purple": colors.HexColor("#f3e8ff"),
    "strong": colors.HexColor("#eaf7f0"),
}

ICON_BG_BY_ORDER = {
    1: "intel",
    2: "intel",
    3: "warn",
    4: "purple",
    5: "intel",
    6: "warn",
    7: "purple",
    8: "intel",
    9: "strong",
    10: "warn",
}

STRONG = colors.HexColor("#198754")
CRITICAL = colors.HexColor("#b91c1c")

_ICON_FLOWABLE_CACHE: dict[tuple[int, int], "SvgDrawingFlowable"] = {}
_ANSWER_ICON_CACHE: dict[str, SvgDrawingFlowable] = {}

_ANSWER_YES_SVG = _ICONS_DIR / "answer-yes.svg"
_ANSWER_NO_SVG = _ICONS_DIR / "answer-no.svg"


class SvgDrawingFlowable(Flowable):
    """Embed an svglib drawing in a platypus table without renderPM/cairo."""

    def __init__(self, drawing, width: float, height: float) -> None:
        super().__init__()
        self.drawing = drawing
        self.width = width
        self.height = height

    def wrap(self, avail_width: float, avail_height: float) -> tuple[float, float]:
        return self.width, self.height

    def draw(self) -> None:
        self.drawing.drawOn(self.canv, 0, 0)


class RoundedIconBackgroundFlowable(Flowable):
    """Tinted circular background behind checklist icon (matches UI rounded-full)."""

    def __init__(
        self,
        child: Flowable,
        box_size: float,
        bg: colors.Color,
    ) -> None:
        super().__init__()
        self.child = child
        self.box_size = box_size
        self.bg = bg
        self.width = box_size
        self.height = box_size

    def wrap(self, avail_width: float, avail_height: float) -> tuple[float, float]:
        return self.box_size, self.box_size

    def draw(self) -> None:
        canvas = self.canv
        radius = self.box_size / 2
        canvas.saveState()
        canvas.setFillColor(self.bg)
        canvas.roundRect(0, 0, self.box_size, self.box_size, radius, fill=1, stroke=0)
        canvas.restoreState()
        child_w, child_h = self.child.wrap(self.box_size, self.box_size)
        inset_x = (self.box_size - child_w) / 2
        inset_y = (self.box_size - child_h) / 2
        self.child.drawOn(canvas, inset_x, inset_y)


def parse_definition_points(definition: str) -> List[Tuple[str, str]]:
    """Return (letter, text) pairs — same rules as frontend parseDefinitionPoints."""
    trimmed = (definition or "").strip()
    if not trimmed:
        return []

    import re

    segments = [
        s.strip()
        for s in re.split(r"\s+(?=[A-Z]\))", trimmed)
        if s.strip()
    ]
    if len(segments) <= 1:
        return [("", trimmed)]

    points: List[Tuple[str, str]] = []
    for segment in segments:
        match = re.match(r"^([A-Z])\)\s*(.+)$", segment)
        if match:
            points.append((match.group(1), match.group(2).strip()))
        else:
            points.append(("", segment))
    return points


def _icon_svg_path(order: int) -> Path:
    path = _ICONS_DIR / f"item-{order:02d}.svg"
    if path.is_file():
        return path
    return _ICONS_DIR / "item-default.svg"


def _load_svg_flowable(path: Path, size: float, cache_key: str) -> Optional[SvgDrawingFlowable]:
    cached = _ANSWER_ICON_CACHE.get(cache_key)
    if cached is not None:
        return cached
    if not path.is_file():
        return None
    try:
        drawing = svg2rlg(str(path))
        if drawing is None:
            return None
        base = max(float(drawing.width or 24), float(drawing.height or 24), 1.0)
        scale = size / base
        drawing.width = size
        drawing.height = size
        drawing.scale(scale, scale)
        flowable = SvgDrawingFlowable(drawing, size, size)
        _ANSWER_ICON_CACHE[cache_key] = flowable
        return flowable
    except Exception:
        return None


def _load_icon_flowable(order: int, size: float) -> Optional[SvgDrawingFlowable]:
    """Load checklist SVG as a vector flowable (no cairo/renderPM required)."""
    cache_key = (order, int(size * 1000))
    cached = _ICON_FLOWABLE_CACHE.get(cache_key)
    if cached is not None:
        return cached

    path = _icon_svg_path(order)
    if not path.is_file():
        return None
    try:
        drawing = svg2rlg(str(path))
        if drawing is None:
            return None
        base = max(float(drawing.width or 64), float(drawing.height or 64), 1.0)
        scale = size / base
        drawing.width = size
        drawing.height = size
        drawing.scale(scale, scale)
        flowable = SvgDrawingFlowable(drawing, size, size)
        _ICON_FLOWABLE_CACHE[cache_key] = flowable
        return flowable
    except Exception:
        return None


def build_status_icon_flowable(
    validated: Optional[bool],
    dash_style,
    size: float = 0.18 * inch,
) -> object:
    """Col 1: green tick (Yes), red cross (No), or em dash."""
    if validated is True:
        icon = _load_svg_flowable(_ANSWER_YES_SVG, size, "answer-yes")
        if icon is not None:
            return icon
    elif validated is False:
        icon = _load_svg_flowable(_ANSWER_NO_SVG, size, "answer-no")
        if icon is not None:
            return icon
    return Paragraph("<para align='center'>—</para>", dash_style)


def build_item_text_flowable(title: str, title_style) -> Paragraph:
    """Col 2: bold title only (no checklist item icon)."""
    return Paragraph(f"<b>{escape(str(title))}</b>", title_style)


def build_yn_text_flowable(
    validated: Optional[bool],
    yes_style,
    no_style,
    neutral_style,
) -> Paragraph:
    """Col 3: Yes / No / — with color (accessible beyond icon-only status)."""
    if validated is True:
        return Paragraph(
            "<para align='center'><font color='#198754'><b>Yes</b></font></para>",
            yes_style,
        )
    if validated is False:
        return Paragraph(
            "<para align='center'><font color='#b91c1c'><b>No</b></font></para>",
            no_style,
        )
    return Paragraph("<para align='center'>—</para>", neutral_style)


def build_item_label_flowable(
    order: int,
    title: str,
    title_style,
    icon_size: float = 0.26 * inch,
    box_size: float = 0.32 * inch,
) -> Table:
    """Icon in tinted circle + bold title (matches ChecklistItemLabel)."""
    icon = _load_icon_flowable(order, icon_size)
    bg_key = ICON_BG_BY_ORDER.get(order, "intel")
    bg = ICON_BG[bg_key]

    icon_cell_content: object
    if icon is not None:
        icon_cell_content = RoundedIconBackgroundFlowable(icon, box_size, bg)
    else:
        icon_cell_content = RoundedIconBackgroundFlowable(
            Paragraph(f"<para align='center'><b>{order}</b></para>", title_style),
            box_size,
            bg,
        )

    title_para = Paragraph(f"<b>{escape(str(title))}</b>", title_style)
    row = Table(
        [[icon_cell_content, title_para]],
        colWidths=[box_size + 4, None],
    )
    row.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return row


def build_definition_flowable(definition: str, body_style, letter_style) -> object:
    """Definition bullets with optional A) B) prefixes."""
    points = parse_definition_points(definition)
    if not points:
        return Paragraph("", body_style)

    if len(points) == 1 and not points[0][0]:
        return Paragraph(escape(str(points[0][1])), body_style)

    rows = []
    for letter, text in points:
        if letter:
            rows.append(
                [
                    Paragraph(f"<b>{letter})</b>", letter_style),
                    Paragraph(escape(text), body_style),
                ]
            )
        else:
            rows.append(
                [
                    Paragraph("", body_style),
                    Paragraph(escape(text), body_style),
                ]
            )

    tbl = Table(rows, colWidths=[0.18 * inch, None])
    tbl.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return tbl


def _yn_pill(text: str, selected: bool, positive: bool, label_style, selected_style) -> Table:
    if selected:
        bg = STRONG if positive else CRITICAL
        text_color = colors.white
        border = bg
        para_style = selected_style
    else:
        bg = colors.white
        text_color = colors.HexColor("#0b1220")
        border = colors.HexColor("#b8c4d4")
        para_style = label_style

    pill = Table([[Paragraph(f"<b>{text}</b>", para_style)]], colWidths=[0.34 * inch])
    pill.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), bg),
                ("TEXTCOLOR", (0, 0), (-1, -1), text_color),
                ("BOX", (0, 0), (-1, -1), 0.75, border),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return pill


def build_yn_flowable(
    validated: Optional[bool],
    label_style,
    selected_style,
) -> Table:
    """Static Yes/No row matching ChecklistYesNoButtons selected state."""
    row = Table(
        [
            [
                _yn_pill("Yes", validated is True, True, label_style, selected_style),
                _yn_pill("No", validated is False, False, label_style, selected_style),
            ]
        ],
        colWidths=[0.36 * inch, 0.36 * inch],
    )
    row.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 1),
                ("RIGHTPADDING", (0, 0), (-1, -1), 1),
            ]
        )
    )
    return row
