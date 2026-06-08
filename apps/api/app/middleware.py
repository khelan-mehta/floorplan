"""Correlation-id + structured request logging middleware."""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response

logger = logging.getLogger("fpg.api")

CORRELATION_HEADER = "x-correlation-id"


def install_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def correlation_and_logging(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        cid = request.headers.get(CORRELATION_HEADER) or uuid.uuid4().hex
        request.state.correlation_id = cid
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("request_failed", extra={"correlation_id": cid, "path": request.url.path})
            raise
        elapsed_ms = (time.perf_counter() - start) * 1000
        response.headers[CORRELATION_HEADER] = cid
        logger.info(
            "request",
            extra={
                "correlation_id": cid,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "elapsed_ms": round(elapsed_ms, 2),
            },
        )
        return response
