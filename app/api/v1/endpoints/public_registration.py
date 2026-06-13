"""Public organization registration endpoints (no authentication)."""
import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.organization import INDUSTRY_OPTIONS
from app.schemas.organization_registration import (
    OrganizationRegistrationCreate,
    OrganizationRegistrationSubmitResponse,
)
from app.services.registration_service import get_registration_service

router = APIRouter()
registration_service = get_registration_service()

_LOGO_MAX_BYTES = 2 * 1024 * 1024
_LOGO_ALLOWED_TYPES = {
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/webp",
    "image/gif",
}


@router.get("/industries")
async def list_public_industry_options():
    """Industry dropdown options for public company signup."""
    return INDUSTRY_OPTIONS


@router.post(
    "/organization-registration",
    response_model=OrganizationRegistrationSubmitResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_organization_registration(
    payload: str = Form(..., description="JSON body matching OrganizationRegistrationCreate"),
    logo: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Submit a company registration request for Super Admin approval."""
    try:
        data = OrganizationRegistrationCreate.model_validate(json.loads(payload))
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid registration payload JSON",
        ) from exc
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.errors(),
        ) from exc

    content_type = (logo.content_type or "").lower()
    if content_type not in _LOGO_ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Logo must be PNG, JPEG, WEBP, or GIF",
        )

    logo_bytes = await logo.read()
    if not logo_bytes or len(logo_bytes) < 32:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid logo file")
    if len(logo_bytes) > _LOGO_MAX_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Logo must be 2MB or smaller")

    try:
        request = await registration_service.submit_registration(
            db,
            data,
            logo_bytes=logo_bytes,
            logo_content_type=content_type,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return OrganizationRegistrationSubmitResponse(
        id=request.id,
        status=request.status,
        message=(
            "Registration submitted successfully. You will receive an email when your "
            "organization has been reviewed."
        ),
    )
