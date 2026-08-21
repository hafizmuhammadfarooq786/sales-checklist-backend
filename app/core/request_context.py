"""
Request-scoped context for activity events (trace_id, IP, UA).
"""
from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from typing import Optional
from uuid import uuid4

from starlette.requests import Request


@dataclass(frozen=True)
class RequestContext:
    trace_id: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


_request_context: ContextVar[Optional[RequestContext]] = ContextVar(
    "request_context", default=None
)


def client_ip_from_request(request: Request) -> Optional[str]:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip() or None
    if request.client:
        return request.client.host
    return None


def bind_request_context(request: Request) -> RequestContext:
    incoming = (request.headers.get("x-trace-id") or "").strip()
    trace_id = incoming[:36] if incoming else str(uuid4())
    ctx = RequestContext(
        trace_id=trace_id,
        ip_address=client_ip_from_request(request),
        user_agent=request.headers.get("user-agent"),
    )
    _request_context.set(ctx)
    request.state.trace_id = trace_id
    return ctx


def get_request_context() -> RequestContext:
    ctx = _request_context.get()
    if ctx is not None:
        return ctx
    return RequestContext(trace_id=str(uuid4()))


def clear_request_context() -> None:
    _request_context.set(None)
