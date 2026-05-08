"""Structured request logger."""
from __future__ import annotations

import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


def configure_logging() -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(20),
    )


class RequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        structlog.contextvars.bind_contextvars(request_id=request_id)
        start = time.perf_counter()
        log = structlog.get_logger("xenia.api")
        try:
            response: Response = await call_next(request)
        except Exception:
            log.exception(
                "request.failed",
                method=request.method,
                path=request.url.path,
            )
            structlog.contextvars.clear_contextvars()
            raise

        elapsed_ms = (time.perf_counter() - start) * 1000.0
        log.info(
            "request.completed",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            elapsed_ms=round(elapsed_ms, 2),
        )
        response.headers["X-Request-Id"] = request_id
        structlog.contextvars.clear_contextvars()
        return response
