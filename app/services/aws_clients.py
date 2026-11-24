"""Shared AWS client helpers (ECS task role or explicit env credentials)."""
from __future__ import annotations

import os

import boto3

from app.core.config import settings


def credential_kwargs() -> dict:
    """
    Explicit credentials for a boto3 client, or nothing.

    Long-lived keys someone put in the settings are passed on, as before.

    Temporary credentials are not. AWS Lambda puts its role's credentials in
    AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY and AWS_SESSION_TOKEN, so the
    settings pick up the first two. Passing those without the token is refused
    by AWS with "InvalidClientTokenId"; that stopped the sign-in code email on
    staging on 2026-11-24. With a session token in the environment, boto3 is
    left to read all three itself.
    """
    if os.environ.get("AWS_SESSION_TOKEN"):
        return {}
    if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
        return {
            "aws_access_key_id": settings.AWS_ACCESS_KEY_ID,
            "aws_secret_access_key": settings.AWS_SECRET_ACCESS_KEY,
        }
    return {}


def s3_client():
    """S3 client using task/instance role when static keys are not configured."""
    return boto3.client("s3", region_name=settings.AWS_REGION, **credential_kwargs())


def lambda_client():
    """Lambda client, same credential rule as s3_client()."""
    return boto3.client("lambda", region_name=settings.AWS_REGION, **credential_kwargs())
