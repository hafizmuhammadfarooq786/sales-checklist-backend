"""
Report Generation API endpoints
Generate and download PDF reports for sales sessions
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime
from typing import Optional
import os

from app.db.session import get_db
from app.models.session import Session, SessionResponse
from app.models.scoring import ScoringResult, CoachingFeedback
from app.models.report import Report
from app.models.checklist import ChecklistItem
from app.api.dependencies import get_current_user_id
from app.services.report_service import get_report_service
from app.services.email_service import email_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/{session_id}/report", status_code=status.HTTP_201_CREATED)
async def generate_report(
    session_id: int,
    include_checklist_details: bool = True,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a PDF report for a session.

    Prerequisites:
    - Session must have scoring results

    Args:
        session_id: Session ID
        include_checklist_details: Include detailed checklist breakdown (default: True)

    Returns:
        Report metadata with download URL
    """
    # Verify session belongs to user
    session_result = await db.execute(
        select(Session).where(
            Session.id == session_id,
            Session.user_id == user_id,
        )
    )
    session = session_result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    # Check if report already exists
    existing_result = await db.execute(
        select(Report).where(Report.session_id == session_id)
    )
    existing = existing_result.scalar_one_or_none()

    if existing and existing.is_generated:
        return {
            "session_id": session_id,
            "report_id": existing.id,
            "pdf_url": existing.pdf_s3_key,
            "file_size": existing.pdf_file_size,
            "generated_at": existing.generated_at,
            "message": "Report already exists"
        }

    # Get scoring results (required)
    scoring_result = await db.execute(
        select(ScoringResult).where(ScoringResult.session_id == session_id)
    )
    scoring = scoring_result.scalar_one_or_none()

    if not scoring:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session must be scored first. Use POST /sessions/{id}/calculate"
        )

    # Get coaching feedback (optional)
    coaching_result = await db.execute(
        select(CoachingFeedback).where(CoachingFeedback.session_id == session_id)
    )
    coaching = coaching_result.scalar_one_or_none()

    # Get checklist responses if requested
    responses_data = None
    if include_checklist_details:
        responses_result = await db.execute(
            select(SessionResponse)
            .where(SessionResponse.session_id == session_id)
            .options(
                selectinload(SessionResponse.item).selectinload(ChecklistItem.category)
            )
            .order_by(SessionResponse.item_id)
        )
        responses = responses_result.scalars().all()

        responses_data = []
        for resp in responses:
            responses_data.append({
                "id": resp.id,
                "item_id": resp.item_id,
                "is_validated": resp.is_validated,
                "confidence": resp.confidence,
                "evidence_text": resp.evidence_text,
                "item": {
                    "id": resp.item.id,
                    "title": resp.item.title,
                    "definition": resp.item.definition,
                    "category": {
                        "id": resp.item.category.id,
                        "name": resp.item.category.name,
                    }
                }
            })

    try:
        # Prepare data for report
        session_data = {
            "customer_name": session.customer_name,
            "opportunity_name": session.opportunity_name,
            "deal_stage": session.deal_stage,
            "created_at": session.created_at
        }

        scoring_data = {
            "total_score": scoring.total_score,
            "risk_band": scoring.risk_band.value if hasattr(scoring.risk_band, 'value') else scoring.risk_band,
            "category_scores": scoring.category_scores,
            "top_strengths": scoring.top_strengths,
            "top_gaps": scoring.top_gaps,
            "items_validated": scoring.items_validated,
            "items_total": scoring.items_total
        }

        coaching_data = None
        if coaching:
            coaching_data = {
                "feedback_text": coaching.feedback_text,
                "strengths": coaching.strengths,
                "improvement_areas": coaching.improvement_areas,
                "action_items": coaching.action_items
            }

        # Generate PDF
        report_service = get_report_service()
        pdf_result = await report_service.generate_session_report(
            session_id=session_id,
            user_id=user_id,
            session_data=session_data,
            scoring_data=scoring_data,
            coaching_data=coaching_data,
            responses_data=responses_data
        )

        # Save or update report record
        if existing:
            existing.pdf_s3_bucket = pdf_result.get('s3_bucket')
            existing.pdf_s3_key = pdf_result.get('pdf_url')
            existing.pdf_file_size = pdf_result.get('file_size')
            existing.generated_at = datetime.utcnow()
            existing.is_generated = True
            report = existing
        else:
            report = Report(
                session_id=session_id,
                pdf_s3_bucket=pdf_result.get('s3_bucket'),
                pdf_s3_key=pdf_result.get('pdf_url'),
                pdf_file_size=pdf_result.get('file_size'),
                generated_at=datetime.utcnow(),
                is_generated=True
            )
            db.add(report)

        await db.commit()
        await db.refresh(report)

        return {
            "session_id": session_id,
            "report_id": report.id,
            "pdf_url": report.pdf_s3_key,
            "file_size": report.pdf_file_size,
            "generated_at": report.generated_at,
            "message": "Report generated successfully"
        }

    except Exception as e:
        logger.error(f"Error generating report for session {session_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate report: {str(e)}"
        )


@router.get("/{session_id}/report")
async def get_report(
    session_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Get report metadata for a session.

    Returns:
        Report metadata with download URL
    """
    # Verify session belongs to user
    session_result = await db.execute(
        select(Session).where(
            Session.id == session_id,
            Session.user_id == user_id,
        )
    )
    session = session_result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    # Get report
    report_result = await db.execute(
        select(Report).where(Report.session_id == session_id)
    )
    report = report_result.scalar_one_or_none()

    if not report or not report.is_generated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found. Use POST to generate."
        )

    return {
        "session_id": session_id,
        "report_id": report.id,
        "pdf_url": report.pdf_s3_key,
        "file_size": report.pdf_file_size,
        "generated_at": report.generated_at,
        "emailed_at": report.emailed_at,
        "emailed_to": report.emailed_to
    }


@router.get("/{session_id}/report/download")
async def download_report(
    session_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Download the PDF report file.

    Returns:
        PDF file as downloadable response
    """
    # Verify session belongs to user
    session_result = await db.execute(
        select(Session).where(
            Session.id == session_id,
            Session.user_id == user_id,
        )
    )
    session = session_result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    # Get report
    report_result = await db.execute(
        select(Report).where(Report.session_id == session_id)
    )
    report = report_result.scalar_one_or_none()

    if not report or not report.is_generated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )

    pdf_path = report.pdf_s3_key

    # Check if it's a local file
    if pdf_path and os.path.exists(pdf_path):
        return FileResponse(
            path=pdf_path,
            filename=f"sales_checklist_report_{session_id}.pdf",
            media_type="application/pdf"
        )

    # If S3, redirect or fetch
    if report.pdf_s3_bucket:
        # For S3 files, you might want to generate a presigned URL
        # For now, return the URL
        raise HTTPException(
            status_code=status.HTTP_302_FOUND,
            headers={"Location": pdf_path}
        )

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="PDF file not found"
    )


@router.post("/{session_id}/report/email")
async def email_report(
    session_id: int,
    recipient_email: Optional[str] = None,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Email the report to specified address or user's email.

    Args:
        session_id: Session ID
        recipient_email: Email address to send to (optional, uses user email if not provided)

    Returns:
        Email delivery status
    """
    # Verify session belongs to user and get user details
    from app.models.user import User

    session_result = await db.execute(
        select(Session).where(
            Session.id == session_id,
            Session.user_id == user_id,
        )
    )
    session = session_result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    # Get user for email
    user_result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Use provided email or user's email
    to_email = recipient_email or user.email

    # Get report
    report_result = await db.execute(
        select(Report).where(Report.session_id == session_id)
    )
    report = report_result.scalar_one_or_none()

    if not report or not report.is_generated:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Report must be generated first"
        )

    try:
        # Send email with report link
        user_name = f"{user.first_name or ''} {user.last_name or ''}".strip() or user.email

        message = f"""
Your The Sales Checklist report for "{session.customer_name}" is ready!

Customer: {session.customer_name}
Opportunity: {session.opportunity_name or 'N/A'}
Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M') if report.generated_at else 'N/A'}

You can download your report from The Sales Checklist dashboard.
"""

        email_sent = email_service.send_notification_email(
            to_emails=[to_email],
            subject=f"The Sales Checklist Report - {session.customer_name}",
            message=message,
            user_name=user_name
        )

        if email_sent:
            # Update report record
            report.emailed_at = datetime.utcnow()
            report.emailed_to = to_email
            await db.commit()

            return {
                "session_id": session_id,
                "emailed_to": to_email,
                "emailed_at": report.emailed_at,
                "message": "Report emailed successfully"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send email. Check email service configuration."
            )

    except Exception as e:
        logger.error(f"Error emailing report for session {session_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to email report: {str(e)}"
        )


@router.post("/{session_id}/report/regenerate")
async def regenerate_report(
    session_id: int,
    include_checklist_details: bool = True,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Regenerate the PDF report (overwrites existing).

    Use after updating scores or coaching feedback.
    """
    # Delete existing report record to force regeneration
    existing_result = await db.execute(
        select(Report).where(Report.session_id == session_id)
    )
    existing = existing_result.scalar_one_or_none()

    if existing:
        existing.is_generated = False
        await db.commit()

    # Call generate_report which will create a new report
    return await generate_report(
        session_id=session_id,
        include_checklist_details=include_checklist_details,
        user_id=user_id,
        db=db
    )
