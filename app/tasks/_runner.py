"""Run an async job from a synchronous Celery task.

`asyncio.run()` builds a fresh event loop and closes it on exit, but the engine
in app.db.session is created once at import and pools its connections. asyncpg
binds each connection to the loop that opened it, so the second task in a worker
process borrows a connection whose loop is already closed:

    RuntimeError: got Future <Future pending> attached to a different loop
    RuntimeError: Event loop is closed

Disposing the engine inside the loop, before that loop closes, means no
connection ever outlives it. The cost is a new connection per task, which is
negligible next to transcription and AI analysis.

This only affects Celery. The API keeps its pool: it serves every request from
one long-lived loop, which is what the pool is designed for.
"""
from __future__ import annotations

import asyncio
from typing import Any, Coroutine, TypeVar

T = TypeVar("T")


async def _run_then_dispose(coro: Coroutine[Any, Any, T]) -> T:
    from app.db.session import engine

    try:
        return await coro
    finally:
        # Inside the loop that owns these connections, so they close cleanly
        # rather than being left for a loop that no longer exists.
        await engine.dispose()


def run_task(coro: Coroutine[Any, Any, T]) -> T:
    """Run `coro` in a private event loop, leaving no pooled connections behind."""
    return asyncio.run(_run_then_dispose(coro))
