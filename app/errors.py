from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import traceback


class ErrorMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        try:
            return await call_next(request)
        except Exception as exc:  # pragma: no cover - defensive
            tb = traceback.format_exc(limit=5)
            return JSONResponse({"error": str(exc), "trace": tb}, status_code=500)
