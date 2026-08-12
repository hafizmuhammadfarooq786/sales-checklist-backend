"""
Trace middleware — attaches X-Trace-Id to every request for activity chains.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.request_context import bind_request_context, clear_request_context


class TraceIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        ctx = bind_request_context(request)
        try:
            response = await call_next(request)
            response.headers["X-Trace-Id"] = ctx.trace_id
            return response
        finally:
            clear_request_context()
