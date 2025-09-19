"""Simple token-bucket rate limiting middleware for FastAPI apps."""

from __future__ import annotations

import time
from typing import Dict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class TokenBucket:
    """Token bucket supporting fractional refill with a configurable burst size."""

    def __init__(self, rate: float, burst: int) -> None:
        self.rate = float(rate)
        self.burst = int(burst)
        self.tokens = float(burst)
        self.timestamp = time.perf_counter()

    def allow(self) -> bool:
        now = time.perf_counter()
        delta = now - self.timestamp
        self.timestamp = now
        self.tokens = min(self.burst, self.tokens + self.rate * delta)
        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Starlette middleware enforcing per-IP token-bucket rate limiting."""

    def __init__(self, app, rate_per_sec: float = 5.0, burst: int = 10) -> None:  # type: ignore[override]
        super().__init__(app)
        self.rate = float(rate_per_sec)
        self.burst = int(burst)
        self._buckets: Dict[str, TokenBucket] = {}

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        client = request.client.host if request.client else "anon"
        bucket = self._buckets.get(client)
        if bucket is None:
            bucket = self._buckets[client] = TokenBucket(self.rate, self.burst)
        if not bucket.allow():
            return JSONResponse({"error": "rate_limited"}, status_code=429)
        return await call_next(request)
