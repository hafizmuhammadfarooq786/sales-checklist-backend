# The Sales Checklist™ API

FastAPI backend for session management, audio upload, Whisper transcription, AI checklist analysis, scoring, coaching, and reports.

## Stack

- **Python 3.11+** (see `Dockerfile`; local venv often uses 3.13+)
- **PostgreSQL** with **SQLAlchemy 2** (async) and **Alembic**
- **Redis** for Celery broker/result backend (optional for local dev if you stay on in-process background tasks)
- **OpenAI** (Whisper + chat models), optional **AWS S3** and **SES**

## Prerequisites

- PostgreSQL database URL ready for the app
- For production-style background jobs: Redis and a running Celery worker

Copy environment template and fill in values:

```bash
cp .env.example .env
```

`DATABASE_URL` must use the **async** driver expected by the app, for example:

`postgresql+asyncpg://USER:PASSWORD@HOST:5432/DATABASE?ssl=require`

## Local setup

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- **API**: http://localhost:8000  
- **OpenAPI**: http://localhost:8000/docs  
- **Health**: http://localhost:8000/health  

## Background transcription (Celery)

Long-running work (transcribe + checklist analysis) can run in a **Celery worker** instead of only on FastAPI `BackgroundTasks`.

| Setting | Meaning |
|--------|---------|
| `USE_CELERY_FOR_TRANSCRIPTION=false` (default) | Uses `BackgroundTasks` after upload / start-transcribe. No worker required. |
| `USE_CELERY_FOR_TRANSCRIPTION=true` | Enqueues `transcription.process_session` on Redis. Requires a worker and broker. |

Broker/result URLs (see `.env.example`):

- `CELERY_BROKER_URL` (e.g. `redis://localhost:6379/1`)
- `CELERY_RESULT_BACKEND` (e.g. `redis://localhost:6379/2`)

Run the worker (from project root, with the same `.env` as the API):

```bash
celery -A app.celery_app worker --loglevel=info
```

If Celery enqueue fails (e.g. Redis down), the API logs a warning and **falls back** to `BackgroundTasks` when possible.

**Upload / transcribe responses** may include a `queue` field: `"celery"` or `"background"`.

Implementation overview:

- **Pipeline**: `app/services/transcription_pipeline.py` (`run_transcription_job`)
- **Dispatch**: `app/services/transcription_dispatcher.py`
- **Task**: `app/tasks/transcription.py`
- **Celery app**: `app/celery_app.py`

## Docker (production compose)

`docker-compose.prod.yml` defines **api**, **redis**, **celery_worker**, and related services. The worker mounts `./uploads` like the API so **local** audio paths remain valid inside the container. Set `USE_CELERY_FOR_TRANSCRIPTION=true` on both **api** and **celery_worker** when using that layout.

Ensure API and worker receive the same secrets (`OPENAI_API_KEY`, AWS credentials if used, and a working `DATABASE_URL`).

## Database migrations

```bash
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

After schema changes, restart the API (and workers). The app configures asyncpg with `statement_cache_size=0` to reduce stale prepared-statement issues across DDL.

## Tests and quality

```bash
pytest
ruff check .
black .
```

(Adjust tooling to match your workflow; `ruff` and `black` are listed in `requirements.txt`.)
