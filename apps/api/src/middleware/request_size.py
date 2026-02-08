# apps/api/src/middleware/request_size.py
"""
Request body size limiting middleware.

Rejects requests whose body exceeds a configurable maximum size,
returning HTTP 413 (Payload Too Large) before the body is fully
consumed.  This protects downstream middleware (e.g. audit logging)
and route handlers from oversized payloads.
"""

import logging

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# 10 MB default
DEFAULT_MAX_BODY_SIZE: int = 10 * 1024 * 1024


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests whose body exceeds *max_body_size* bytes."""

    def __init__(self, app, max_body_size: int = DEFAULT_MAX_BODY_SIZE):
        super().__init__(app)
        self.max_body_size = max_body_size

    async def dispatch(self, request: Request, call_next):
        # ----------------------------------------------------------
        # Fast path: check the Content-Length header when present.
        # ----------------------------------------------------------
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                declared_size = int(content_length)
            except (ValueError, TypeError):
                declared_size = 0

            if declared_size > self.max_body_size:
                logger.warning(
                    "Request rejected: Content-Length %d exceeds limit %d | %s %s",
                    declared_size,
                    self.max_body_size,
                    request.method,
                    request.url.path,
                )
                return JSONResponse(
                    status_code=413,
                    content={
                        "detail": "Payload too large",
                        "max_bytes": self.max_body_size,
                    },
                )

        # ----------------------------------------------------------
        # Slow path: no Content-Length (e.g. chunked transfer).
        # Read the body in chunks and abort if the cumulative size
        # exceeds the limit.
        # ----------------------------------------------------------
        if request.method.upper() in {"POST", "PUT", "PATCH"}:
            body_chunks: list[bytes] = []
            total_size = 0

            async for chunk in request.stream():
                total_size += len(chunk)
                if total_size > self.max_body_size:
                    logger.warning(
                        "Request rejected: streamed body exceeds limit %d | %s %s",
                        self.max_body_size,
                        request.method,
                        request.url.path,
                    )
                    return JSONResponse(
                        status_code=413,
                        content={
                            "detail": "Payload too large",
                            "max_bytes": self.max_body_size,
                        },
                    )
                body_chunks.append(chunk)

            # Re-attach the consumed body so downstream handlers can
            # read it via `await request.body()`.
            full_body = b"".join(body_chunks)

            async def _receive():
                return {"type": "http.request", "body": full_body}

            request._receive = _receive

        return await call_next(request)
