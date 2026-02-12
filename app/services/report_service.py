"""
Report Generation Service
Generates PDF reports for sales sessions using ReportLab
"""
import os
import tempfile
import re
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

    def _sanitize_filename(self, name: str) -> str:
        """
        Sanitize a string to be used as a filename.
        Removes or replaces invalid characters, limits length.
        
        Args:
            name: Original name string
            
        Returns:
            Sanitized filename-safe string
        """
        if not name:
            return "report"
        
        # Remove leading/trailing whitespace
        name = name.strip()
        
        # Replace spaces with underscores
        name = name.replace(' ', '_')
        
        # Remove or replace invalid filename characters
        # Keep only alphanumeric, underscores, hyphens, and dots
        name = re.sub(r'[^a-zA-Z0-9_\-.]', '', name)
        
        # Remove multiple consecutive underscores
        name = re.sub(r'_+', '_', name)
        
        # Limit length to 50 characters
        if len(name) > 50:
            name = name[:50]
        
        # If empty after sanitization, use default
        if not name:
            return "report"
        
        return name

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

            # Get customer name for PDF title
            customer_name = session_data.get('customer_name', 'Report')
            pdf_title = f"The Sales Checklist Report - {customer_name}" if customer_name else "The Sales Checklist Report"

            # Create PDF in memory
            buffer = BytesIO()
            doc = SimpleDocTemplate(
                buffer,
                pagesize=letter,
                rightMargin=0.75*inch,
                leftMargin=0.75*inch,
                topMargin=0.75*inch,
                bottomMargin=0.75*inch,
                title=pdf_title,
                author="The Sales Checklist"
            )

            # Build report content
            story = []
            story.extend(self._build_header(session_data, scoring_data))
            story.extend(self._build_score_summary(scoring_data))
            
            # Only show checklist details (coaching feedback removed per user request)
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

            # Get customer name for filename
            customer_name = session_data.get('customer_name', '')
            sanitized_name = self._sanitize_filename(customer_name)
            
            # Upload to S3
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            filename = f"{sanitized_name}_{timestamp}.pdf"
            s3_key = f"reports/{user_id}/{session_id}/{filename}"

            try:
                s3_service = get_s3_service()
                s3_url = s3_service.upload_file(
                    temp_file.name,
                    s3_key,
                    content_type="application/pdf",
                    bucket_name=settings.S3_BUCKET_REPORTS
                )
                
                # Verify the file was actually uploaded
                # Note: We'll trust the upload succeeded if no exception was raised
                # The presigned URL generation will fail if the file doesn't exist
                storage_type = "s3"
                print(f"Successfully uploaded report to S3: {s3_key}")
            except Exception as s3_error:
                print(f"S3 upload failed, using local storage: {s3_error}")
                # Fall back to local storage
                local_dir = f"uploads/reports/{user_id}/{session_id}"
                os.makedirs(local_dir, exist_ok=True)
                local_path = f"{local_dir}/{filename}"

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
            "The Sales Checklist<super>TM</super> Report",
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
        """Build score summary section - centered score and health status"""
        elements = []

        elements.append(Paragraph("Overall Score", self.styles['SectionHeader']))
        elements.append(Spacer(1, 20))

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

        # Build centered score display
        score_text = f"{score:.0f}/100"
        risk_text = f"<b>{band_labels.get(risk_band, 'Unknown').upper()}</b>"
        
        # Score style - centered
        score_style = ParagraphStyle(
            'DynamicScore',
            parent=self.styles['Normal'],
            fontSize=48,
            alignment=1,  # Center
            textColor=score_color,
            spaceAfter=15,  # Space between score and health label
            leading=56,
            spaceBefore=0
        )
        
        # Health label style - centered
        band_style = ParagraphStyle(
            'BandLabel',
            parent=self.styles['Normal'],
            fontSize=16,
            alignment=1,  # Center
            textColor=score_color,
            spaceBefore=0,
            spaceAfter=0,
            leading=20
        )

        # Add centered score and health label
        elements.append(Paragraph(score_text, score_style))
        elements.append(Paragraph(risk_text, band_style))
        elements.append(Spacer(1, 20))

        return elements

    def _build_checklist_details(self, responses_data: List[Dict[str, Any]]) -> List:
        """Build detailed checklist responses section - shows only checklist items with Yes/No answers"""
        elements = []

        elements.append(PageBreak())
        elements.append(Paragraph("Checklist Details", self.styles['SectionHeader']))
        elements.append(Spacer(1, 10))

        # Build a single table with all checklist items
        table_data = [['Item', 'Answer']]
        
        # Sort by item order if available, otherwise by item_id
        sorted_responses = sorted(
            responses_data,
            key=lambda r: r.get('item', {}).get('order', r.get('item_id', 0))
        )
        
        for resp in sorted_responses:
            # Safely extract item data with better error handling
            item = resp.get('item') or {}
            
            # Handle both dict and object-like structures
            if not isinstance(item, dict):
                # If item is an object, try to get attributes
                title = getattr(item, 'title', None) or 'Unknown Item'
            else:
                title = item.get('title') or item.get('name') or 'Unknown Item'
            
            # Get validation status
            validated = resp.get('is_validated')
            
            # Determine answer
            if validated is True:
                answer = 'Yes'
            elif validated is False:
                answer = 'No'
            else:
                answer = 'N/A'
            
            # Only add items with valid titles
            if title and title != 'Unknown Item':
                table_data.append([title, answer])

        # Create table if we have data
        if len(table_data) > 1:
            item_table = Table(table_data, colWidths=[5.5*inch, 1.5*inch])
            item_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('ALIGN', (1, 0), (1, -1), 'CENTER'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ]))
            elements.append(item_table)
        else:
            elements.append(Paragraph(
                "No checklist items available.",
                self.styles['BodyText']
            ))

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
            f"The Sales Checklist<super>TM</super> | Generated {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')} | Confidential",
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
