"""
Background jobs when the API runs on AWS Lambda (staging).

On ECS the API process keeps running after it answers, so work can be left to
FastAPI BackgroundTasks, or queued on Celery for a separate worker. On Lambda
neither holds: the process is frozen the moment the response is sent, and there
is no Redis for Celery. Work scheduled "for after the response" would simply
never run, with no error anywhere.

So when LAMBDA_WORKER_FUNCTION is set:

- long jobs (transcription, AI analysis) are handed to a second Lambda function
  with an asynchronous invoke. That function runs this same codebase with
  LAMBDA_WORKER_MODE on and receives each job at POST /events;
- short follow-ups (one email) are done before the response instead of after.

There is deliberately no fallback to BackgroundTasks if the invoke fails. A
fallback would report success and then drop the job. The caller sees the error.

Unset, which is the default and what production uses, nothing here changes
anything: every caller keeps its Celery and BackgroundTasks paths.
"""
import json
import logging
from typing import Any, Awaitable, Callable, Dict

from fastapi import BackgroundTasks

from app.core.config import settings

logger = logging.getLogger(__name__)


async def _transcription(session_id: int, file_path: str) -> None:
    from app.services.transcription_pipeline import run_transcription_job

    await run_transcription_job(session_id, file_path)


async def _knowledge_document(document_id: int) -> None:
    from app.services.knowledge_ingestion_service import process_knowledge_document

    await process_knowledge_document(document_id)


async def _session_intelligence(session_id: int, organization_id: int) -> None:
    from app.services.knowledge_session_intelligence_service import (
        run_session_intelligence_job,
    )

    await run_session_intelligence_job(session_id, organization_id)


async def _coaching(session_id: int, total_score: float, risk_band: str) -> None:
    from app.api.v1.endpoints.sessions import generate_coaching_in_background
    from app.models.scoring import RiskBand

    # The band travels as its text value; a job's arguments must be plain JSON.
    await generate_coaching_in_background(session_id, total_score, RiskBand(risk_band))


# Names match the Celery task names where a Celery task exists. Imports are
# inside the functions so that importing this module stays cheap and free of
# import cycles (the endpoints import it, and one job imports an endpoint).
JOBS: Dict[str, Callable[..., Awaitable[None]]] = {
    "transcription.process_session": _transcription,
    "knowledge_base.process_document": _knowledge_document,
    "knowledge_base.analyze_session": _session_intelligence,
    "coaching.generate": _coaching,
}


def lambda_worker_enabled() -> bool:
    """True when background work must go to the Lambda worker function."""
    return bool((settings.LAMBDA_WORKER_FUNCTION or "").strip())


def send_to_lambda_worker(job: str, **kwargs: Any) -> None:
    """Hand a job to the worker function. Raises if it could not be handed over."""
    if job not in JOBS:
        raise ValueError(f"Unknown background job: {job}")

    from app.services.aws_clients import lambda_client

    response = lambda_client().invoke(
        FunctionName=settings.LAMBDA_WORKER_FUNCTION.strip(),
        InvocationType="Event",  # asynchronous: returns once Lambda has queued it
        Payload=json.dumps({"job": job, "kwargs": kwargs}).encode(),
    )
    status_code = response.get("StatusCode")
    if status_code != 202:
        raise RuntimeError(f"Lambda worker did not accept {job}: status {status_code}")
    logger.info("Handed %s to Lambda worker: %s", job, kwargs)


async def run_job(job: str, kwargs: Dict[str, Any]) -> None:
    """Run a job in this process. Called by the worker function's /events route."""
    if job not in JOBS:
        raise ValueError(f"Unknown background job: {job}")
    await JOBS[job](**kwargs)


async def run_after_response(
    background_tasks: BackgroundTasks,
    func: Callable[..., Awaitable[Any]],
    **kwargs: Any,
) -> None:
    """
    For a short follow-up such as one email.

    Normally it runs after the response, as before. On Lambda nothing runs after
    the response, so it runs now and the request waits for it.
    """
    if lambda_worker_enabled():
        await func(**kwargs)
        return
    background_tasks.add_task(func, **kwargs)
