import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.errors import ErrorMiddleware
from app.ratelimit import RateLimitMiddleware
from app.security import require_api_key


class RequestSizeLimitMiddleware:
    def __init__(self, app, max_bytes: int = 2_000_000):
        self.app = app
        self.max = int(max_bytes)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = dict(scope.get("headers") or [])
        content_length = headers.get(b"content-length")
        if content_length is not None:
            try:
                if int(content_length) > self.max:
                    response = JSONResponse({"error": "request_too_large"}, status_code=413)
                    await response(scope, receive, send)
                    return
            except Exception:  # pragma: no cover - defensive
                pass
        await self.app(scope, receive, send)


def _csv_env(name: str) -> list[str]:
    value = os.getenv(name, "")
    return [item.strip() for item in value.split(",") if item.strip()]


def attach_common(app: FastAPI):
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
    async def _request_id(request: Request, call_next):
        response: Response = await call_next(request)
        response.headers.setdefault("x-request-id", os.getenv("REQUEST_ID_PREFIX", "bp-") + "local")
        return response

    return app


def api_auth_dep():
    if os.getenv("API_KEY"):
        return require_api_key
    return lambda: None
