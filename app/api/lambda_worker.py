"""
Entry point for background jobs on the Lambda worker function (staging).

The Lambda Web Adapter delivers every event that is not a web request to
POST /events, with the event as the JSON body. The API hands jobs over as
{"job": name, "kwargs": {...}} (see app/services/background_jobs.py).

This router is mounted only when LAMBDA_WORKER_MODE is true, and the worker
function has no public address: the only way to reach it is an AWS-signed
invoke by a role allowed to call it. It must never be mounted on the API.

The job runs to completion inside the request, which keeps the function alive
for as long as the job takes (Lambda's limit is 15 minutes).
"""
import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.services.background_jobs import JOBS, run_job

logger = logging.getLogger(__name__)

router = APIRouter()


class JobEvent(BaseModel):
    job: str
    kwargs: Dict[str, Any] = Field(default_factory=dict)


@router.post("/events")
async def handle_job_event(event: JobEvent) -> Dict[str, str]:
    if event.job not in JOBS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown background job: {event.job}",
        )
    logger.info("Lambda worker: starting %s %s", event.job, event.kwargs)
    await run_job(event.job, event.kwargs)
    logger.info("Lambda worker: finished %s", event.job)
    return {"status": "done", "job": event.job}
