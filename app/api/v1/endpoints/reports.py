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
from app.models.scoring import ScoringResult, CoachingFeedback, RiskBand
from app.models.report import Report
from app.models.checklist import ChecklistItem
from app.models.user import User
from app.api.dependencies import get_current_user, get_session_access_filter
from app.services.report_service import get_report_service
from app.services.email_service import email_service

router = APIRouter()
logger = logging.getLogger(__name__)


def get_report_url(report: Report, request=None) -> Optional[str]:
    """
    Generate a presigned URL or accessible URL for report PDF.

    Args:
        report: Report instance
        request: Optional FastAPI Request object to get base URL

    Returns:
        URL string if PDF exists, None otherwise
    """
    if not report.pdf_s3_key:
        return None

    from app.services.s3_service import get_s3_service
    from app.core.config import settings

    # Extract S3 key from pdf_s3_key (handle both full URL and key-only formats)
    s3_key = report.pdf_s3_key
    
    # If pdf_s3_key is a full URL, extract just the key part
    if s3_key.startswith('http'):
        # Extract key from URL like: https://bucket.s3.region.amazonaws.com/key/path
        try:
            if '.s3.' in s3_key:
                # Extract everything after the bucket name
                parts = s3_key.split('.s3.')
                if len(parts) > 1:
                    key_part = parts[1].split('/', 1)
                    if len(key_part) > 1:
                        s3_key = key_part[1]  # Get the key path
                    else:
                        # Fallback: try to extract from URL path
                        from urllib.parse import urlparse
                        parsed = urlparse(s3_key)
                        s3_key = parsed.path.lstrip('/')
        except Exception as e:
            logger.warning(f"Failed to extract S3 key from URL {report.pdf_s3_key}: {e}")
            # If extraction fails and it's a full URL, return it as-is (might be a public URL)
            if s3_key.startswith('http'):
                return s3_key

    # If PDF is stored in S3, generate presigned URL
    if report.pdf_s3_bucket:
        try:
            s3_service = get_s3_service()
            
            # Verify file exists in S3 before generating presigned URL
            # Note: check_file_exists uses default bucket, so we'll skip this check
            # and let the presigned URL generation handle errors
            
            presigned_url = s3_service.generate_presigned_url(
                s3_key,  # Use extracted key, not the full URL
                expiration=3600,  # 1 hour
                bucket_name=report.pdf_s3_bucket
            )
            if presigned_url:
                logger.info(f"Generated presigned URL for report: bucket={report.pdf_s3_bucket}, key={s3_key}")
                return presigned_url
            else:
                logger.error(f"Failed to generate presigned URL: bucket={report.pdf_s3_bucket}, key={s3_key}")
        except Exception as e:
            logger.error(f"Failed to generate presigned URL for report (bucket={report.pdf_s3_bucket}, key={s3_key}): {e}", exc_info=True)

    # For local storage, construct full URL
    # Try to get base URL from request if available
    base_url = "http://localhost:8000"  # Default fallback
    if request:
        base_url = str(request.base_url).rstrip("/")
    elif hasattr(settings, "API_BASE_URL") and settings.API_BASE_URL:
        base_url = settings.API_BASE_URL.rstrip("/")

    # Construct the full URL for local files
    pdf_path = s3_key
    if not pdf_path.startswith("http"):
        # Remove leading slash if present
        if pdf_path.startswith("/"):
            pdf_path = pdf_path[1:]
        # Construct full URL
        return f"{base_url}/api/v1/uploads/{pdf_path}"

    return pdf_path


@router.post("/{session_id}/report", status_code=status.HTTP_201_CREATED)
async def generate_report(
    session_id: int,
    include_checklist_details: bool = True,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a PDF report for a session.
    
    This endpoint ALWAYS regenerates the report, even if one already exists.
    It recalculates scores from the latest checklist data before generating the report.
    All checklist details are always included in the report.

    Prerequisites:
    - Session must have checklist responses

    Args:
        session_id: Session ID
        include_checklist_details: (Deprecated - always True) Always includes all checklist details

    Returns:
        Report metadata with download URL

    RBAC:
    - REP: Can access own sessions
    - MANAGER: Can access team sessions
    - ADMIN: Can access org sessions
    - SYSTEM_ADMIN: Can access all sessions
    """
    # Verify session access with RBAC
    access_filter = get_session_access_filter(current_user)
    session_result = await db.execute(
        select(Session).where(
            Session.id == session_id,
            access_filter
        )
    )
    session = session_result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or access denied"
        )

    # Check if report already exists (we'll update it, not return early)
    existing_result = await db.execute(
        select(Report).where(Report.session_id == session_id)
    )
    existing = existing_result.scalar_one_or_none()

    # Always recalculate scores from latest checklist data before generating report
    # Get all responses with checklist items and categories (latest data)
    responses_result = await db.execute(
        select(SessionResponse)
        .where(SessionResponse.session_id == session_id)
        .options(
            selectinload(SessionResponse.item).selectinload(ChecklistItem.category)
        )
        .order_by(SessionResponse.item_id)
    )
    responses = responses_result.scalars().all()

    if not responses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No checklist responses found for this session. Cannot generate report."
        )

    # Recalculate score from latest checklist data
    total_score = 0
    validated_count = 0
    category_scores = {}
    
    for response in responses:
        item = response.item
        category = item.category
        
        # Track category
        if category.id not in category_scores:
            category_scores[category.id] = {
                "name": category.name,
                "score": 0,
                "max_score": 0
            }
        
        category_scores[category.id]["max_score"] += 10

        # Calculate score for this item
        # Use user_answer if provided, otherwise use ai_answer
        final_answer = response.user_answer if response.user_answer is not None else response.ai_answer

        item_score = 0
        if final_answer is True:
            item_score = 10
            total_score += 10
            validated_count += 1

        category_scores[category.id]["score"] += item_score

    # Calculate percentage score (0-100)
    max_possible_score = len(responses) * 10
    percentage_score = (total_score / max_possible_score * 100) if max_possible_score > 0 else 0

    # Determine risk band
    if percentage_score >= 80:
        risk_band = RiskBand.GREEN
    elif percentage_score >= 60:
        risk_band = RiskBand.YELLOW
    else:
        risk_band = RiskBand.RED

    # Get or create scoring result and update with recalculated values
    scoring_result = await db.execute(
        select(ScoringResult).where(ScoringResult.session_id == session_id)
    )
    scoring = scoring_result.scalar_one_or_none()

    if scoring:
        # Update existing scoring result with recalculated values
        scoring.total_score = percentage_score
        scoring.risk_band = risk_band
        scoring.items_validated = validated_count
        scoring.items_total = len(responses)
        scoring.category_scores = category_scores
        # Update top_strengths and top_gaps if needed (simplified for now)
        scoring.top_strengths = []
        scoring.top_gaps = []
    else:
        # Create new scoring result
        scoring = ScoringResult(
            session_id=session_id,
            total_score=percentage_score,
            risk_band=risk_band,
            items_validated=validated_count,
            items_total=len(responses),
            category_scores=category_scores,
            top_strengths=[],
            top_gaps=[]
        )
        db.add(scoring)

    await db.commit()
    await db.refresh(scoring)

    # Get coaching feedback (optional)
    coaching_result = await db.execute(
        select(CoachingFeedback).where(CoachingFeedback.session_id == session_id)
    )
    coaching = coaching_result.scalar_one_or_none()

    # Always include all checklist details in the report
    # Use the responses we already loaded for score calculation
    responses_data = []
    for resp in responses:
                # Ensure item is loaded
                if not resp.item:
                    logger.warning(f"SessionResponse {resp.id} has no item loaded for session {session_id}")
                    continue
                    
                # Ensure category is loaded
                if not resp.item.category:
                    logger.warning(f"ChecklistItem {resp.item.id} has no category loaded for session {session_id}")
                    continue
                
                # Get item title - use a fallback if title is None or empty
                item_title = resp.item.title
                if not item_title or item_title.strip() == '':
                    logger.warning(f"ChecklistItem {resp.item.id} has no title, using fallback")
                    item_title = f"Checklist Item {resp.item.id}"
                
                # Determine final answer: user_answer takes precedence over ai_answer
                # user_answer if not None, otherwise ai_answer
                final_answer = resp.user_answer if resp.user_answer is not None else resp.ai_answer
                
                responses_data.append({
                    "id": resp.id,
                    "item_id": resp.item_id,
                    "is_validated": final_answer,  # True = Yes, False = No
                    "ai_answer": resp.ai_answer,
                    "user_answer": resp.user_answer,
                    "confidence": getattr(resp, 'confidence', None),
                    "evidence_text": getattr(resp, 'evidence_text', None),
                    "item": {
                        "id": resp.item.id,
                        "title": item_title,
                        "order": getattr(resp.item, 'order', resp.item_id),  # Use order if available
                        "definition": getattr(resp.item, 'definition', '') or '',
                        "category": {
                            "id": resp.item.category.id,
                            "name": resp.item.category.name or 'Uncategorized',
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
            user_id=current_user.id,
            session_data=session_data,
            scoring_data=scoring_data,
            coaching_data=coaching_data,
            responses_data=responses_data
        )

        # Save or update report record
        # Store only the S3 key (not the full URL) for proper presigned URL generation
        s3_key = pdf_result.get('s3_key') or pdf_result.get('pdf_url')
        
        # If s3_key is a full URL, extract just the key part
        if s3_key and s3_key.startswith('http'):
            # Extract key from URL like: https://bucket.s3.region.amazonaws.com/key/path
            try:
                # Remove protocol and domain, keep only the path after bucket name
                if '.s3.' in s3_key:
                    # Extract everything after the bucket name
                    parts = s3_key.split('.s3.')
                    if len(parts) > 1:
                        key_part = parts[1].split('/', 1)
                        if len(key_part) > 1:
                            s3_key = key_part[1]  # Get the key path
                        else:
                            # Fallback: try to extract from URL path
                            from urllib.parse import urlparse
                            parsed = urlparse(s3_key)
                            s3_key = parsed.path.lstrip('/')
            except Exception as e:
                logger.warning(f"Failed to extract S3 key from URL {s3_key}: {e}")
                # If extraction fails, use the full URL (will be handled in get_report_url)
        
        if existing:
            existing.pdf_s3_bucket = pdf_result.get('s3_bucket')
            existing.pdf_s3_key = s3_key  # Store only the key, not the full URL
            existing.pdf_file_size = pdf_result.get('file_size')
            existing.generated_at = datetime.utcnow()
            existing.is_generated = True
            report = existing
        else:
            report = Report(
                session_id=session_id,
                pdf_s3_bucket=pdf_result.get('s3_bucket'),
                pdf_s3_key=s3_key,  # Store only the key, not the full URL
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    request: Optional[object] = None,
    auto_generate: bool = True,  # Auto-generate if report doesn't exist
):
    """
    Get report metadata for a session.
    If report doesn't exist and auto_generate=True, generates it on-demand.

    Returns:
        Report metadata with download URL (pre-signed if S3)

    RBAC:
    - REP: Can access own sessions
    - MANAGER: Can access team sessions
    - ADMIN: Can access org sessions
    - SYSTEM_ADMIN: Can access all sessions
    """
    # Verify session access with RBAC
    access_filter = get_session_access_filter(current_user)
    session_result = await db.execute(
        select(Session).where(
            Session.id == session_id,
            access_filter
        )
    )
    session = session_result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or access denied"
        )

    # Get report
    report_result = await db.execute(
        select(Report).where(Report.session_id == session_id)
    )
    report = report_result.scalar_one_or_none()

    # Auto-generate report if it doesn't exist
    if (not report or not report.is_generated) and auto_generate:
        logger.info(f"Report not found for session {session_id}, generating on-demand...")
        try:
            # Call generate_report internally
            result = await generate_report(
                session_id=session_id,
                include_checklist_details=True,
                current_user=current_user,
                db=db
            )
            # Refresh report from DB
            report_result = await db.execute(
                select(Report).where(Report.session_id == session_id)
            )
            report = report_result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Failed to auto-generate report for session {session_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate report: {str(e)}"
            )

    if not report or not report.is_generated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found and could not be generated."
        )

    # Generate presigned URL for PDF
    pdf_url = get_report_url(report, request)

    return {
        "session_id": session_id,
        "report_id": report.id,
        "pdf_url": pdf_url,
        "file_size": report.pdf_file_size,
        "generated_at": report.generated_at,
        "emailed_at": report.emailed_at,
        "emailed_to": report.emailed_to
    }


@router.get("/{session_id}/report/download")
async def download_report(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    auto_generate: bool = True,  # Auto-generate if report doesn't exist
):
    """
    Get the download URL for the PDF report.
    If report doesn't exist and auto_generate=True, generates it on-demand.

    Returns:
        JSON with download_url (pre-signed for S3, direct for local files)

    RBAC:
    - REP: Can access own sessions
    - MANAGER: Can access team sessions
    - ADMIN: Can access org sessions
    - SYSTEM_ADMIN: Can access all sessions
    """
    # Verify session access with RBAC
    access_filter = get_session_access_filter(current_user)
    session_result = await db.execute(
        select(Session).where(
            Session.id == session_id,
            access_filter
        )
    )
    session = session_result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or access denied"
        )

    # Get report
    report_result = await db.execute(
        select(Report).where(Report.session_id == session_id)
    )
    report = report_result.scalar_one_or_none()

    # Auto-generate report if it doesn't exist
    if (not report or not report.is_generated) and auto_generate:
        logger.info(f"Report not found for session {session_id}, generating on-demand for download...")
        try:
            # Check if session has scoring results (required for report)
            scoring_result = await db.execute(
                select(ScoringResult).where(ScoringResult.session_id == session_id)
            )
            scoring = scoring_result.scalar_one_or_none()

            if not scoring:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Session must be scored first. Please calculate scores before generating report."
                )

            # Call generate_report internally
            await generate_report(
                session_id=session_id,
                include_checklist_details=True,
                current_user=current_user,
                db=db
            )
            # Refresh report from DB
            report_result = await db.execute(
                select(Report).where(Report.session_id == session_id)
            )
            report = report_result.scalar_one_or_none()
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to auto-generate report for session {session_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate report: {str(e)}"
            )

    if not report or not report.is_generated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found and could not be generated."
        )

    # Generate download URL (pre-signed for S3, local URL for files)
    download_url = get_report_url(report)

    if not download_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate download URL"
        )

    return {
        "session_id": session_id,
        "download_url": download_url,
        "file_size": report.pdf_file_size,
        "filename": f"sales_checklist_report_{session_id}.pdf"
    }


@router.post("/{session_id}/report/email")
async def email_report(
    session_id: int,
    recipient_email: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Email the report to specified address or user's email.

    Args:
        session_id: Session ID
        recipient_email: Email address to send to (optional, uses user email if not provided)

    Returns:
        Email delivery status

    RBAC:
    - REP: Can access own sessions
    - MANAGER: Can access team sessions
    - ADMIN: Can access org sessions
    - SYSTEM_ADMIN: Can access all sessions
    """
    # Verify session access with RBAC
    access_filter = get_session_access_filter(current_user)
    session_result = await db.execute(
        select(Session).where(
            Session.id == session_id,
            access_filter
        )
    )
    session = session_result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or access denied"
        )

    # Use provided email or user's email
    to_email = recipient_email or current_user.email

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
        user_name = f"{current_user.first_name or ''} {current_user.last_name or ''}".strip() or current_user.email

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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Regenerate the PDF report (overwrites existing).

    Use after updating scores or coaching feedback.

    RBAC:
    - REP: Can access own sessions
    - MANAGER: Can access team sessions
    - ADMIN: Can access org sessions
    - SYSTEM_ADMIN: Can access all sessions
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
        current_user=current_user,
        db=db
    )
