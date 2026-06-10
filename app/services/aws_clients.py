"""Shared AWS client helpers (ECS task role or explicit env credentials)."""
from __future__ import annotations

import boto3

from app.core.config import settings


def s3_client():
    """S3 client using task/instance role when static keys are not configured."""
    kwargs: dict = {"region_name": settings.AWS_REGION}
    if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
        kwargs["aws_access_key_id"] = settings.AWS_ACCESS_KEY_ID
        kwargs["aws_secret_access_key"] = settings.AWS_SECRET_ACCESS_KEY
    return boto3.client("s3", **kwargs)
