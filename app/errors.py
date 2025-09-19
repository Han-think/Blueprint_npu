"""Global error middleware for Blueprint APIs."""

from __future__ import annotations

import traceback
from typing import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class ErrorMiddleware(BaseHTTPMiddleware):
    """Wrap requests and return JSON error payloads on failure."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        try:
            return await call_next(request)
        except Exception as exc:  # pragma: no cover - defensive hardening
            trace = traceback.format_exc(limit=5)
            return JSONResponse({"error": str(exc), "trace": trace}, status_code=500)

