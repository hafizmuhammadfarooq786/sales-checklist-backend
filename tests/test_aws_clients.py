"""
AWS credentials for the S3, SES and Lambda clients.

What this protects: on AWS Lambda the runtime puts TEMPORARY credentials in
AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY and AWS_SESSION_TOKEN. A client built
from the key and secret alone, without the token, is refused by AWS with
"InvalidClientTokenId". That is what stopped the sign-in code email on staging
on 2026-11-24. Every client must leave temporary credentials to boto3.

What green does not prove: that AWS accepts the call. That needs the deployed
function.
"""
import pytest

from app.core.config import settings
from app.services import aws_clients


@pytest.fixture
def created(monkeypatch):
    """Record what boto3.client is called with, without touching AWS."""
    calls = []

    def fake_client(service, **kwargs):
        calls.append((service, kwargs))
        return object()

    monkeypatch.setattr("boto3.client", fake_client)
    return calls


def _keys_in_settings(monkeypatch, key="AKIDEXAMPLE", secret="example-secret"):
    monkeypatch.setattr(settings, "AWS_ACCESS_KEY_ID", key)
    monkeypatch.setattr(settings, "AWS_SECRET_ACCESS_KEY", secret)


def test_temporary_credentials_are_left_to_boto3(monkeypatch):
    _keys_in_settings(monkeypatch)
    monkeypatch.setenv("AWS_SESSION_TOKEN", "temporary-token")
    assert aws_clients.credential_kwargs() == {}


def test_long_lived_keys_are_still_passed(monkeypatch):
    _keys_in_settings(monkeypatch)
    monkeypatch.delenv("AWS_SESSION_TOKEN", raising=False)
    assert aws_clients.credential_kwargs() == {
        "aws_access_key_id": "AKIDEXAMPLE",
        "aws_secret_access_key": "example-secret",
    }


def test_no_keys_means_the_role_is_used(monkeypatch):
    _keys_in_settings(monkeypatch, key="", secret="")
    monkeypatch.delenv("AWS_SESSION_TOKEN", raising=False)
    assert aws_clients.credential_kwargs() == {}


def test_s3_and_lambda_clients_never_send_half_a_temporary_credential(monkeypatch, created):
    _keys_in_settings(monkeypatch)
    monkeypatch.setenv("AWS_SESSION_TOKEN", "temporary-token")
    aws_clients.s3_client()
    aws_clients.lambda_client()
    assert [service for service, _ in created] == ["s3", "lambda"]
    for service, kwargs in created:
        assert "aws_access_key_id" not in kwargs, service
        assert "aws_secret_access_key" not in kwargs, service


def test_email_client_never_sends_half_a_temporary_credential(monkeypatch, created):
    from app.services.email_service import EmailService

    _keys_in_settings(monkeypatch)
    monkeypatch.setenv("AWS_SESSION_TOKEN", "temporary-token")
    EmailService._build_ses_client()
    assert created and created[-1][0] == "ses"
    assert "aws_access_key_id" not in created[-1][1]
    assert "aws_secret_access_key" not in created[-1][1]
