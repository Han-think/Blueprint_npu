"""Shared FastAPI bootstrap utilities (middleware and auth helpers)."""

from __future__ import annotations

import os
from typing import Awaitable, Callable, List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.errors import ErrorMiddleware
from app.ratelimit import RateLimitMiddleware
from app.security import require_api_key


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests that exceed a configured Content-Length."""

    def __init__(self, app: FastAPI, max_bytes: int = 2_000_000) -> None:
        super().__init__(app)
        self._max_bytes = int(max_bytes)

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > self._max_bytes:
                    return JSONResponse({"error": "request_too_large"}, status_code=413)
            except ValueError:
                # If the header is invalid fall through to request handling.
                pass
        return await call_next(request)


def _csv_env(name: str) -> List[str]:
    raw = os.getenv(name, "")
    return [item.strip() for item in raw.split(",") if item.strip()]


def attach_common(app: FastAPI) -> FastAPI:
    """Attach shared middleware such as error handling, rate limiting and CORS."""

    app.add_middleware(ErrorMiddleware)

    rate = float(os.getenv("RATELIMIT_RATE", "5.0"))
    burst = int(os.getenv("RATELIMIT_BURST", "10"))
    app.add_middleware(RateLimitMiddleware, rate_per_sec=rate, burst=burst)

    max_bytes = int(os.getenv("REQUEST_MAX_BYTES", "2000000"))
    app.add_middleware(RequestSizeLimitMiddleware, max_bytes=max_bytes)

    origins = _csv_env("CORS_ORIGINS")
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.middleware("http")
    async def _request_id_middleware(request: Request, call_next):  # type: ignore[override]
        response: Response = await call_next(request)
        prefix = os.getenv("REQUEST_ID_PREFIX", "bp-")
        response.headers.setdefault("x-request-id", f"{prefix}local")
        return response

    return app


def api_auth_dep():
    """Return an API-key dependency if configured, else a no-op dependency."""

    if os.getenv("API_KEY"):
        return require_api_key
    return lambda: None

