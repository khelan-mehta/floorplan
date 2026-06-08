"""RFC 7807 problem+json errors and exception handlers."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class ProblemError(Exception):
    """Raise to return an RFC 7807 problem+json response."""

    def __init__(
        self,
        status_code: int,
        title: str,
        detail: str | None = None,
        type_: str = "about:blank",
        **extra: Any,
    ) -> None:
        self.status_code = status_code
        self.title = title
        self.detail = detail
        self.type = type_
        self.extra = extra
        super().__init__(detail or title)


def _problem(
    request: Request, status_code: int, title: str, detail: str | None, type_: str, **extra: Any
) -> JSONResponse:
    body: dict[str, Any] = {
        "type": type_,
        "title": title,
        "status": status_code,
        "instance": str(request.url.path),
    }
    if detail:
        body["detail"] = detail
    cid = getattr(request.state, "correlation_id", None)
    if cid:
        body["correlation_id"] = cid
    body.update(extra)
    return JSONResponse(
        status_code=status_code, content=body, media_type="application/problem+json"
    )


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ProblemError)
    async def _handle_problem(request: Request, exc: ProblemError) -> JSONResponse:
        return _problem(request, exc.status_code, exc.title, exc.detail, exc.type, **exc.extra)

    @app.exception_handler(StarletteHTTPException)
    async def _handle_http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        title = exc.detail if isinstance(exc.detail, str) else "HTTP error"
        return _problem(request, exc.status_code, title, None, "about:blank")

    @app.exception_handler(RequestValidationError)
    async def _handle_validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        return _problem(
            request,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Request validation failed",
            None,
            "about:blank",
            errors=exc.errors(),
        )
