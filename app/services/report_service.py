"""
Report Generation Service
Generates PDF reports for sales sessions using ReportLab
"""
import os
import tempfile
from datetime import datetime
from typing import Dict, Any, Optional, List
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, PageBreak, HRFlowable
)
from reportlab.graphics.shapes import Drawing, Rect
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.barcharts import VerticalBarChart

from app.core.config import settings
from app.services.s3_service import get_s3_service


class ReportService:
    """Service for generating PDF reports"""

    def __init__(self):
        """Initialize report service"""
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Setup custom paragraph styles"""
        # Helper to add style only if it doesn't exist
        def add_style_if_not_exists(style):
            try:
                self.styles.add(style)
            except KeyError:
                pass  # Style already exists

        # Title style
        add_style_if_not_exists(ParagraphStyle(
            name='ReportTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            spaceAfter=20,
            textColor=colors.HexColor('#1a1a2e'),
            alignment=1  # Center
        ))

        # Subtitle style
        add_style_if_not_exists(ParagraphStyle(
            name='ReportSubtitle',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceAfter=12,
            textColor=colors.HexColor('#4a4a6a'),
            alignment=1
        ))

        # Section header
        add_style_if_not_exists(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=16,
            spaceBefore=20,
            spaceAfter=10,
            textColor=colors.HexColor('#667eea'),
            borderPadding=5
        ))

        # Score display
        add_style_if_not_exists(ParagraphStyle(
            name='ScoreDisplay',
            parent=self.styles['Normal'],
            fontSize=48,
            alignment=1,
            textColor=colors.HexColor('#1a1a2e')
        ))

        # Body text - override existing BodyText style
        self.styles['BodyText'].fontSize = 11
        self.styles['BodyText'].spaceBefore = 6
        self.styles['BodyText'].spaceAfter = 6
        self.styles['BodyText'].leading = 14

    async def generate_session_report(
        self,
        session_id: int,
        user_id: int,
        session_data: Dict[str, Any],
        scoring_data: Dict[str, Any],
        coaching_data: Optional[Dict[str, Any]] = None,
        responses_data: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive PDF report for a session

        Args:
            session_id: Session ID
            user_id: User ID for S3 path
            session_data: Session details (customer_name, opportunity_name, etc.)
            scoring_data: Scoring results (score, risk_band, category_scores, etc.)
            coaching_data: Optional coaching feedback
            responses_data: Optional list of checklist responses

        Returns:
            Dict with PDF URL, file size, and metadata
        """
        try:
            print(f"Generating PDF report for session {session_id}")

            # Create PDF in memory
            buffer = BytesIO()
            doc = SimpleDocTemplate(
                buffer,
                pagesize=letter,
                rightMargin=0.75*inch,
                leftMargin=0.75*inch,
                topMargin=0.75*inch,
                bottomMargin=0.75*inch
            )

            # Build report content
            story = []
            story.extend(self._build_header(session_data, scoring_data))
            story.extend(self._build_score_summary(scoring_data))
            story.extend(self._build_category_breakdown(scoring_data))

            if coaching_data:
                story.extend(self._build_coaching_section(coaching_data))

            if responses_data:
                story.extend(self._build_checklist_details(responses_data))

            story.extend(self._build_footer())

            # Build PDF
            doc.build(story)

            # Get PDF bytes
            pdf_bytes = buffer.getvalue()
            buffer.close()

            # Save to temp file for S3 upload
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            temp_file.write(pdf_bytes)
            temp_file.close()

            file_size = len(pdf_bytes)

            # Upload to S3
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            s3_key = f"reports/{user_id}/{session_id}/report_{timestamp}.pdf"

            try:
                s3_service = get_s3_service()
                s3_url = s3_service.upload_file(
                    temp_file.name,
                    s3_key,
                    content_type="application/pdf",
                    bucket_name=settings.S3_BUCKET_REPORTS
                )
                storage_type = "s3"
            except Exception as s3_error:
                print(f"S3 upload failed, using local storage: {s3_error}")
                # Fall back to local storage
                local_dir = f"uploads/reports/{user_id}/{session_id}"
                os.makedirs(local_dir, exist_ok=True)
                local_path = f"{local_dir}/report_{timestamp}.pdf"

                import shutil
                shutil.copy(temp_file.name, local_path)
                s3_url = local_path
                storage_type = "local"
            finally:
                os.unlink(temp_file.name)

            print(f"PDF report generated: {s3_url} ({file_size} bytes)")

            return {
                "pdf_url": s3_url,
                "s3_bucket": settings.S3_BUCKET_REPORTS if storage_type == "s3" else None,
                "s3_key": s3_key if storage_type == "s3" else None,
                "file_size": file_size,
                "storage_type": storage_type,
                "generated_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            print(f"Error generating PDF report: {e}")
            raise e

    def _build_header(
        self,
        session_data: Dict[str, Any],
        scoring_data: Dict[str, Any]
    ) -> List:
        """Build report header section"""
        elements = []

        # Title
        elements.append(Paragraph(
            "Sales Checklist<super>TM</super> Report",
            self.styles['ReportTitle']
        ))

        # Subtitle with date
        report_date = datetime.utcnow().strftime('%B %d, %Y')
        elements.append(Paragraph(
            f"Generated on {report_date}",
            self.styles['ReportSubtitle']
        ))

        elements.append(Spacer(1, 20))

        # Session info table
        customer_name = session_data.get('customer_name', 'N/A')
        opportunity_name = session_data.get('opportunity_name', 'N/A')
        deal_stage = session_data.get('deal_stage', 'N/A')
        created_at = session_data.get('created_at', '')

        if isinstance(created_at, datetime):
            created_at = created_at.strftime('%Y-%m-%d %H:%M')

        info_data = [
            ['Customer', customer_name, 'Deal Stage', deal_stage],
            ['Opportunity', opportunity_name, 'Session Date', str(created_at)[:16] if created_at else 'N/A'],
        ]

        info_table = Table(info_data, colWidths=[1.2*inch, 2.3*inch, 1.2*inch, 2.3*inch])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#667eea')),
            ('TEXTCOLOR', (2, 0), (2, -1), colors.HexColor('#667eea')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
        ]))

        elements.append(info_table)
        elements.append(Spacer(1, 20))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e0e0e0')))

        return elements

    def _build_score_summary(self, scoring_data: Dict[str, Any]) -> List:
        """Build score summary section"""
        elements = []

        elements.append(Paragraph("Overall Score", self.styles['SectionHeader']))

        score = scoring_data.get('total_score', 0)
        risk_band = scoring_data.get('risk_band', 'red')

        # Risk band colors
        band_colors = {
            'green': colors.HexColor('#27ae60'),
            'yellow': colors.HexColor('#f39c12'),
            'red': colors.HexColor('#e74c3c')
        }
        band_labels = {
            'green': 'Healthy',
            'yellow': 'Caution',
            'red': 'At Risk'
        }

        score_color = band_colors.get(risk_band, colors.gray)

        # Score display
        score_style = ParagraphStyle(
            'DynamicScore',
            parent=self.styles['ScoreDisplay'],
            textColor=score_color
        )
        elements.append(Paragraph(f"{score:.0f}/100", score_style))

        # Risk band label
        band_style = ParagraphStyle(
            'BandLabel',
            parent=self.styles['Normal'],
            fontSize=16,
            alignment=1,
            textColor=score_color
        )
        elements.append(Paragraph(
            f"<b>{band_labels.get(risk_band, 'Unknown').upper()}</b>",
            band_style
        ))

        elements.append(Spacer(1, 15))

        # Stats row
        validated = scoring_data.get('items_validated', 0)
        total = scoring_data.get('items_total', 92)

        stats_data = [[
            f"Items Validated: {validated}/{total}",
            f"Completion: {validated/total*100:.0f}%" if total > 0 else "0%"
        ]]

        stats_table = Table(stats_data, colWidths=[3.5*inch, 3.5*inch])
        stats_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#4a4a6a')),
        ]))
        elements.append(stats_table)

        elements.append(Spacer(1, 10))

        # Strengths and Gaps
        strengths = scoring_data.get('top_strengths', [])
        gaps = scoring_data.get('top_gaps', [])

        if strengths or gaps:
            sg_data = [['Top Strengths', 'Areas for Improvement']]

            max_items = max(len(strengths), len(gaps))
            for i in range(max_items):
                strength = strengths[i] if i < len(strengths) else ''
                gap = gaps[i] if i < len(gaps) else ''
                sg_data.append([f"+ {strength}" if strength else '', f"- {gap}" if gap else ''])

            sg_table = Table(sg_data, colWidths=[3.5*inch, 3.5*inch])
            sg_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('TEXTCOLOR', (0, 0), (0, 0), colors.HexColor('#27ae60')),
                ('TEXTCOLOR', (1, 0), (1, 0), colors.HexColor('#e74c3c')),
                ('TEXTCOLOR', (0, 1), (0, -1), colors.HexColor('#27ae60')),
                ('TEXTCOLOR', (1, 1), (1, -1), colors.HexColor('#e74c3c')),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            elements.append(sg_table)

        return elements

    def _build_category_breakdown(self, scoring_data: Dict[str, Any]) -> List:
        """Build category breakdown section"""
        elements = []

        elements.append(Spacer(1, 20))
        elements.append(Paragraph("Category Breakdown", self.styles['SectionHeader']))

        category_scores = scoring_data.get('category_scores', {})

        if not category_scores:
            elements.append(Paragraph(
                "No category data available.",
                self.styles['BodyText']
            ))
            return elements

        # Build category table
        table_data = [['Category', 'Score', 'Status']]

        for cat_id, cat_data in category_scores.items():
            if isinstance(cat_data, dict):
                name = cat_data.get('name', f'Category {cat_id}')
                score = cat_data.get('score', 0)
                max_score = cat_data.get('max_score', 100)
                percentage = (score / max_score * 100) if max_score > 0 else 0

                if percentage >= 80:
                    status = 'Excellent'
                elif percentage >= 60:
                    status = 'Good'
                elif percentage >= 40:
                    status = 'Fair'
                else:
                    status = 'Needs Work'

                table_data.append([name, f"{percentage:.0f}%", status])

        cat_table = Table(table_data, colWidths=[3.5*inch, 1.5*inch, 2*inch])
        cat_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ]))
        elements.append(cat_table)

        return elements

    def _build_coaching_section(self, coaching_data: Dict[str, Any]) -> List:
        """Build coaching feedback section"""
        elements = []

        elements.append(PageBreak())
        elements.append(Paragraph("Coaching Feedback", self.styles['SectionHeader']))

        # Feedback text
        feedback_text = coaching_data.get('feedback_text', '')
        if feedback_text:
            elements.append(Paragraph(feedback_text, self.styles['BodyText']))
            elements.append(Spacer(1, 15))

        # Action items
        action_items = coaching_data.get('action_items', [])
        if action_items:
            elements.append(Paragraph(
                "<b>Action Items for Next Call:</b>",
                self.styles['BodyText']
            ))
            for i, item in enumerate(action_items, 1):
                elements.append(Paragraph(
                    f"{i}. {item}",
                    self.styles['BodyText']
                ))

        return elements

    def _build_checklist_details(self, responses_data: List[Dict[str, Any]]) -> List:
        """Build detailed checklist responses section"""
        elements = []

        elements.append(PageBreak())
        elements.append(Paragraph("Checklist Details", self.styles['SectionHeader']))

        # Group by category
        categories = {}
        for response in responses_data:
            item = response.get('item', {})
            category = item.get('category', {})
            cat_name = category.get('name', 'Uncategorized')

            if cat_name not in categories:
                categories[cat_name] = []
            categories[cat_name].append(response)

        for cat_name, items in categories.items():
            elements.append(Paragraph(
                f"<b>{cat_name}</b>",
                self.styles['BodyText']
            ))

            table_data = [['Item', 'Status']]
            for resp in items:
                item = resp.get('item', {})
                title = item.get('title', 'Unknown')
                validated = resp.get('is_validated')

                if validated is True:
                    status = 'Yes'
                elif validated is False:
                    status = 'No'
                else:
                    status = 'N/A'

                table_data.append([title, status])

            if len(table_data) > 1:
                item_table = Table(table_data, colWidths=[5.5*inch, 1.5*inch])
                item_table.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('ALIGN', (1, 0), (1, -1), 'CENTER'),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                    ('TOPPADDING', (0, 0), (-1, -1), 4),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
                ]))
                elements.append(item_table)
                elements.append(Spacer(1, 10))

        return elements

    def _build_footer(self) -> List:
        """Build report footer"""
        elements = []

        elements.append(Spacer(1, 30))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e0e0e0')))
        elements.append(Spacer(1, 10))

        footer_style = ParagraphStyle(
            'Footer',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#999999'),
            alignment=1
        )

        elements.append(Paragraph(
            f"Sales Checklist<super>TM</super> | Generated {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')} | Confidential",
            footer_style
        ))

        return elements


# Global service instance (lazy initialization)
_report_service: Optional[ReportService] = None


def get_report_service() -> ReportService:
    """Get or create the report service singleton"""
    global _report_service
    if _report_service is None:
        _report_service = ReportService()
    return _report_service
