"""
Direct audio upload to S3 (staging on Lambda).

What these protect:
- production stays on the old path: with the setting off both routes are 404;
- the size cap and content type are inside the signature, so S3 enforces them
  whatever the browser sends;
- a user cannot register a file that sits outside their own session folder;
- an unsupported type or an oversized file is refused before anything is signed.

What green does not prove: that S3 accepts the form from a browser (bucket
CORS), or that the file's bytes are really audio. Those need the deployed app.
"""
import base64
import json

import boto3
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user_id
from app.api.v1.endpoints import uploads
from app.core.config import settings
from app.db.session import get_db
from app.services.s3_service import S3Service


class _NoDatabase:
    """Fails the test if a route reaches the database before refusing."""

    async def execute(self, *args, **kwargs):
        raise AssertionError("the route touched the database")


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(uploads.router, prefix="/sessions")
    app.dependency_overrides[get_current_user_id] = lambda: 7

    async def no_db():
        yield _NoDatabase()

    app.dependency_overrides[get_db] = no_db
    return TestClient(app)


def test_setting_is_off_by_default():
    assert settings.DIRECT_UPLOADS_ENABLED is False


def test_both_routes_are_404_when_the_setting_is_off(client):
    ask = client.post(
        "/sessions/128/upload-url",
        json={"filename": "a.webm", "content_type": "audio/webm", "file_size": 10},
    )
    done = client.post("/sessions/128/upload-complete", json={"key": "audio/7/128/a.webm"})
    assert ask.status_code == 404 and ask.json()["detail"]["error"] == "DIRECT_UPLOADS_DISABLED"
    assert done.status_code == 404 and done.json()["detail"]["error"] == "DIRECT_UPLOADS_DISABLED"


def test_unsupported_type_is_refused_before_signing(client, monkeypatch):
    monkeypatch.setattr(settings, "DIRECT_UPLOADS_ENABLED", True)
    response = client.post(
        "/sessions/128/upload-url",
        json={"filename": "a.exe", "content_type": "application/x-msdownload", "file_size": 10},
    )
    assert response.status_code == 415


def test_oversized_file_is_refused_before_signing(client, monkeypatch):
    monkeypatch.setattr(settings, "DIRECT_UPLOADS_ENABLED", True)
    too_big = settings.MAX_AUDIO_FILE_SIZE_MB * 1024 * 1024 + 1
    response = client.post(
        "/sessions/128/upload-url",
        json={"filename": "a.webm", "content_type": "audio/webm", "file_size": too_big},
    )
    assert response.status_code == 413
    assert response.json()["detail"]["error"] == "FILE_TOO_LARGE"


def test_key_outside_the_users_session_folder_is_refused(client, monkeypatch):
    monkeypatch.setattr(settings, "DIRECT_UPLOADS_ENABLED", True)
    for key in (
        "audio/8/128/a.webm",          # another user's folder
        "audio/7/129/a.webm",          # another session
        "audio/7/128/../../8/1/a",     # traversal
        "audio/7/128/sub/a.webm",      # nested
        "audio/7/128/",                # no file name
        "reports/7/128/a.webm",        # another area of the bucket
    ):
        response = client.post("/sessions/128/upload-complete", json={"key": key})
        assert response.status_code == 400, key
        assert response.json()["detail"]["error"] == "INVALID_UPLOAD_KEY", key


def test_owns_audio_key_accepts_the_key_the_api_hands_out():
    key = uploads.audio_key_prefix(7, 128) + "128_abc123.webm"
    assert uploads.owns_audio_key(key, 7, 128)
    assert not uploads.owns_audio_key(key, 7, 12)   # 128 must not match session 12
    assert not uploads.owns_audio_key(key, 70, 128)


def test_signature_fixes_key_type_and_size(monkeypatch):
    """Signing is local arithmetic: no network, made-up credentials."""
    service = S3Service.__new__(S3Service)
    service.bucket_name = "stage-audio"
    service.s3_client = boto3.client(
        "s3", region_name="us-east-2",
        aws_access_key_id="test", aws_secret_access_key="test",
    )
    form = service.generate_presigned_upload("audio/7/128/a.webm", "audio/webm", 1000, 600)
    conditions = json.loads(base64.b64decode(form["fields"]["policy"]))["conditions"]

    assert form["fields"]["key"] == "audio/7/128/a.webm"
    assert {"key": "audio/7/128/a.webm"} in conditions
    assert {"bucket": "stage-audio"} in conditions
    assert {"Content-Type": "audio/webm"} in conditions
    assert ["content-length-range", 1, 1000] in conditions
    assert service.object_url("audio/7/128/a.webm") == (
        f"https://stage-audio.s3.{settings.AWS_REGION}.amazonaws.com/audio/7/128/a.webm"
    )


# ---------------------------------------------------------------------------
# Voice notes and knowledge documents (app/api/v1/endpoints/direct_uploads.py)
# ---------------------------------------------------------------------------

from types import SimpleNamespace

from app.api.dependencies import get_current_user
from app.api.v1.endpoints import direct_uploads
from app.models.user import UserRole

AUDIO = {"filename": "note.webm", "content_type": "audio/webm", "file_size": 10}
PDF = {"filename": "guide.pdf", "content_type": "application/pdf", "file_size": 10}


def _client_as(role, organization_id=3):
    user = SimpleNamespace(id=7, role=role, organization_id=organization_id, team_id=None)
    app = FastAPI()
    app.include_router(direct_uploads.notes_router, prefix="/sessions")
    app.include_router(direct_uploads.knowledge_router, prefix="/organization/knowledge-base")
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[direct_uploads.require_admin] = lambda: user

    async def no_db():
        yield _NoDatabase()

    app.dependency_overrides[get_db] = no_db
    return TestClient(app)


def test_new_routes_are_404_when_the_setting_is_off():
    client = _client_as(UserRole.ADMIN)
    calls = [
        ("/sessions/128/notes/audio/upload-url", AUDIO),
        ("/sessions/128/notes/audio/upload-complete", {"key": "manager_notes/7/128/a.webm"}),
        ("/organization/knowledge-base/documents/upload-url", PDF),
        ("/organization/knowledge-base/documents/upload-complete",
         {"key": "knowledge-base/3/a.pdf", "filename": "a.pdf"}),
    ]
    for path, body in calls:
        response = client.post(path, json=body)
        assert response.status_code == 404, path
        assert response.json()["detail"]["error"] == "DIRECT_UPLOADS_DISABLED", path


def test_a_rep_cannot_get_a_voice_note_form(monkeypatch):
    monkeypatch.setattr(settings, "DIRECT_UPLOADS_ENABLED", True)
    client = _client_as(UserRole.REP)
    assert client.post("/sessions/128/notes/audio/upload-url", json=AUDIO).status_code == 403
    done = client.post(
        "/sessions/128/notes/audio/upload-complete", json={"key": "manager_notes/7/128/a.webm"}
    )
    assert done.status_code == 403


def test_voice_note_type_and_size_are_checked_before_signing(monkeypatch):
    monkeypatch.setattr(settings, "DIRECT_UPLOADS_ENABLED", True)
    client = _client_as(UserRole.MANAGER)
    not_audio = client.post(
        "/sessions/128/notes/audio/upload-url", json={**AUDIO, "content_type": "application/pdf"}
    )
    too_big = client.post(
        "/sessions/128/notes/audio/upload-url",
        json={**AUDIO, "file_size": direct_uploads.VOICE_NOTE_MAX_BYTES + 1},
    )
    assert not_audio.status_code == 400
    assert too_big.status_code == 400 and "10MB" in too_big.json()["detail"]


def test_voice_note_key_outside_the_managers_folder_is_refused(monkeypatch):
    monkeypatch.setattr(settings, "DIRECT_UPLOADS_ENABLED", True)
    client = _client_as(UserRole.MANAGER)
    for key in (
        "manager_notes/8/128/a.webm",     # another manager
        "manager_notes/7/129/a.webm",     # another session
        "manager_notes/7/128/../a.webm",  # traversal
        "audio/7/128/a.webm",             # a session recording, not a note
    ):
        response = client.post("/sessions/128/notes/audio/upload-complete", json={"key": key})
        assert response.status_code == 400, key
        assert response.json()["detail"]["error"] == "INVALID_UPLOAD_KEY", key


def test_knowledge_type_and_size_are_checked_before_signing(monkeypatch):
    monkeypatch.setattr(settings, "DIRECT_UPLOADS_ENABLED", True)
    client = _client_as(UserRole.ADMIN)
    path = "/organization/knowledge-base/documents/upload-url"
    wrong_type = client.post(path, json={**PDF, "content_type": "application/zip"})
    too_big = client.post(
        path, json={**PDF, "file_size": settings.KNOWLEDGE_BASE_MAX_FILE_BYTES + 1}
    )
    assert wrong_type.status_code == 400 and "Supported types" in wrong_type.json()["detail"]
    assert too_big.status_code == 400 and "maximum allowed size" in too_big.json()["detail"]


def test_knowledge_key_outside_the_organizations_folder_is_refused(monkeypatch):
    monkeypatch.setattr(settings, "DIRECT_UPLOADS_ENABLED", True)
    client = _client_as(UserRole.ADMIN, organization_id=3)
    for key in (
        "knowledge-base/4/a.pdf",       # another organization
        "knowledge-base/30/a.pdf",      # 3 must not match 30
        "knowledge-base/3/x/a.pdf",     # nested
        "knowledge-base/3/../4/a.pdf",  # traversal
    ):
        response = client.post(
            "/organization/knowledge-base/documents/upload-complete",
            json={"key": key, "filename": "a.pdf"},
        )
        assert response.status_code == 400, key
        assert response.json()["detail"]["error"] == "INVALID_UPLOAD_KEY", key


def test_knowledge_form_is_signed_for_the_normalised_type(monkeypatch):
    """The browser may send 'application/pdf; charset=binary'. S3 must hold the
    clean type, because indexing later picks its reader from it."""
    monkeypatch.setattr(settings, "DIRECT_UPLOADS_ENABLED", True)
    signed = {}

    class FakeS3:
        def generate_presigned_upload(self, key, content_type, max_bytes, expiration):
            signed.update(key=key, content_type=content_type, max_bytes=max_bytes)
            return {"url": "https://s3.example/", "fields": {"key": key}}

    monkeypatch.setattr(direct_uploads, "get_s3_service", lambda: FakeS3())
    response = _client_as(UserRole.ADMIN, organization_id=3).post(
        "/organization/knowledge-base/documents/upload-url",
        json={**PDF, "content_type": "application/pdf; charset=binary"},
    )
    assert response.status_code == 200
    assert signed["content_type"] == "application/pdf"
    assert signed["max_bytes"] == settings.KNOWLEDGE_BASE_MAX_FILE_BYTES
    assert direct_uploads.key_is_directly_under(response.json()["key"], "knowledge-base/3/")
    assert response.json()["key"].endswith(".pdf")
