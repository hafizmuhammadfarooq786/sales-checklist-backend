"""
Background work on Lambda (staging), and proof that the default path is untouched.

What these protect: on Lambda a job left to BackgroundTasks never runs and
nothing reports it. Each test below fails if a hand-off point stops sending its
job to the worker, sends the wrong payload, or quietly falls back.

What green does not prove: that AWS accepts the invoke, or that the worker
function finishes the job. Those need the deployed functions.
"""
import json

import pytest
from fastapi import BackgroundTasks, FastAPI
from fastapi.testclient import TestClient

from app.core.config import settings
from app.services import background_jobs


class FakeLambda:
    def __init__(self, status_code=202, error=None):
        self.calls = []
        self.status_code = status_code
        self.error = error

    def invoke(self, **kwargs):
        if self.error:
            raise self.error
        self.calls.append(kwargs)
        return {"StatusCode": self.status_code}


@pytest.fixture
def worker(monkeypatch):
    """Lambda worker switched on, with the AWS client replaced by a recorder."""
    fake = FakeLambda()
    monkeypatch.setattr(settings, "LAMBDA_WORKER_FUNCTION", "stage-worker")
    monkeypatch.setattr("app.services.aws_clients.lambda_client", lambda: fake)
    return fake


def _sent(fake):
    assert len(fake.calls) == 1
    call = fake.calls[0]
    assert call["FunctionName"] == "stage-worker"
    assert call["InvocationType"] == "Event"
    return json.loads(call["Payload"])


def test_default_is_off():
    assert settings.LAMBDA_WORKER_FUNCTION == ""
    assert settings.LAMBDA_WORKER_MODE is False
    assert background_jobs.lambda_worker_enabled() is False


def test_transcription_goes_to_the_worker(worker):
    from app.services.transcription_dispatcher import schedule_transcription

    tasks = BackgroundTasks()
    assert schedule_transcription(128, "https://bucket/audio.webm", tasks) == "lambda"
    assert _sent(worker) == {
        "job": "transcription.process_session",
        "kwargs": {"session_id": 128, "file_path": "https://bucket/audio.webm"},
    }
    assert tasks.tasks == []


def test_transcription_does_not_fall_back_when_the_worker_refuses(monkeypatch):
    from app.services.transcription_dispatcher import schedule_transcription

    monkeypatch.setattr(settings, "LAMBDA_WORKER_FUNCTION", "stage-worker")
    monkeypatch.setattr(
        "app.services.aws_clients.lambda_client",
        lambda: FakeLambda(error=RuntimeError("access denied")),
    )
    tasks = BackgroundTasks()
    with pytest.raises(RuntimeError):
        schedule_transcription(128, "audio.webm", tasks)
    assert tasks.tasks == []


def test_a_status_other_than_accepted_is_an_error(monkeypatch):
    monkeypatch.setattr(settings, "LAMBDA_WORKER_FUNCTION", "stage-worker")
    monkeypatch.setattr(
        "app.services.aws_clients.lambda_client", lambda: FakeLambda(status_code=500)
    )
    with pytest.raises(RuntimeError):
        background_jobs.send_to_lambda_worker(
            "knowledge_base.process_document", document_id=1
        )


def test_transcription_without_the_worker_is_unchanged(monkeypatch):
    from app.services.transcription_dispatcher import schedule_transcription

    monkeypatch.setattr(settings, "USE_CELERY_FOR_TRANSCRIPTION", False)
    tasks = BackgroundTasks()
    assert schedule_transcription(128, "audio.webm", tasks) == "background"
    assert len(tasks.tasks) == 1


def test_knowledge_document_goes_to_the_worker(worker):
    from app.api.v1.endpoints.knowledge_base import _enqueue_document_processing

    tasks = BackgroundTasks()
    _enqueue_document_processing(tasks, 7)
    assert _sent(worker) == {
        "job": "knowledge_base.process_document",
        "kwargs": {"document_id": 7},
    }
    assert tasks.tasks == []


def test_session_intelligence_goes_to_the_worker(worker):
    from app.api.v1.endpoints.sessions import _enqueue_session_intelligence

    tasks = BackgroundTasks()
    _enqueue_session_intelligence(tasks, 128, 3)
    assert _sent(worker) == {
        "job": "knowledge_base.analyze_session",
        "kwargs": {"session_id": 128, "organization_id": 3},
    }
    assert tasks.tasks == []


def test_unknown_job_is_refused_before_any_call(worker):
    with pytest.raises(ValueError):
        background_jobs.send_to_lambda_worker("no.such.job", x=1)
    assert worker.calls == []


async def test_coaching_job_turns_the_band_back_into_the_enum(monkeypatch):
    from app.api.v1.endpoints import sessions
    from app.models.scoring import RiskBand

    seen = {}

    async def fake_generate(session_id, total_score, risk_band):
        seen.update(session_id=session_id, total_score=total_score, risk_band=risk_band)

    monkeypatch.setattr(sessions, "generate_coaching_in_background", fake_generate)
    await background_jobs.run_job(
        "coaching.generate",
        {"session_id": 128, "total_score": 70.0, "risk_band": RiskBand.GREEN.value},
    )
    assert seen == {"session_id": 128, "total_score": 70.0, "risk_band": RiskBand.GREEN}


async def test_short_follow_up_runs_before_the_response_on_lambda(worker):
    ran = []

    async def send_email(to):
        ran.append(to)

    tasks = BackgroundTasks()
    await background_jobs.run_after_response(tasks, send_email, to="rep@example.com")
    assert ran == ["rep@example.com"]
    assert tasks.tasks == []
    assert worker.calls == []


async def test_short_follow_up_is_left_for_after_the_response_elsewhere():
    ran = []

    async def send_email(to):
        ran.append(to)

    tasks = BackgroundTasks()
    await background_jobs.run_after_response(tasks, send_email, to="rep@example.com")
    assert ran == []
    assert len(tasks.tasks) == 1


def _worker_app():
    from app.api.lambda_worker import router

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_worker_route_runs_the_named_job(monkeypatch):
    ran = []

    async def fake_job(document_id):
        ran.append(document_id)

    monkeypatch.setitem(background_jobs.JOBS, "knowledge_base.process_document", fake_job)
    response = _worker_app().post(
        "/events",
        json={"job": "knowledge_base.process_document", "kwargs": {"document_id": 7}},
    )
    assert response.status_code == 200
    assert ran == [7]


def test_worker_route_refuses_an_unknown_job():
    response = _worker_app().post("/events", json={"job": "no.such.job", "kwargs": {}})
    assert response.status_code == 400


def test_worker_route_is_not_on_the_api():
    from app.main import app

    assert "/events" not in {route.path for route in app.routes}
