import json

import time


from starlette.middleware.base import BaseHTTPMiddleware


class SimpleLogger(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):  # type: ignore[override]
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        try:
            print(
                json.dumps(
                    {
                        "path": request.url.path,
                        "status": response.status_code,
                        "ms": round(elapsed_ms, 2),
                    }
                )
            )
        except Exception:
            pass
        return response
