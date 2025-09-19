import time
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class TokenBucket:
    def __init__(self, rate: float, burst: int):
        self.rate = float(rate)
        self.burst = int(burst)
        self.tokens = float(burst)
        self.ts = time.perf_counter()

    def allow(self) -> bool:
        now = time.perf_counter()
        dt = now - self.ts
        self.ts = now
        self.tokens = min(self.burst, self.tokens + self.rate * dt)
        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, rate_per_sec: float = 5.0, burst: int = 10):
        super().__init__(app)
        self.rate = rate_per_sec
        self.burst = burst
        self.buckets = {}

    async def dispatch(self, request, call_next):
        ip = request.client.host if request.client else "anon"
        bucket = self.buckets.get(ip)
        if bucket is None:
            bucket = self.buckets[ip] = TokenBucket(self.rate, self.burst)
        if not bucket.allow():
            return JSONResponse({"error": "rate_limited"}, status_code=429)
        return await call_next(request)
