from __future__ import annotations

from fastapi import FastAPI, Request
from starlette.responses import PlainTextResponse

app = FastAPI(title="Metrics")
_requests = 0
_errors = 0


@app.middleware("http")
async def count_requests(request: Request, call_next):
    global _requests, _errors
    _requests += 1
    try:
        response = await call_next(request)
        return response
    except Exception:
        _errors += 1
        raise


@app.get("/metrics")
def metrics():
    lines = [
        "# HELP bp_requests_total Total HTTP requests",
        "# TYPE bp_requests_total counter",
        f"bp_requests_total {_requests}",
        "# HELP bp_errors_total Total unhandled errors",
        "# TYPE bp_errors_total counter",
        f"bp_errors_total {_errors}",
    ]
    return PlainTextResponse("\n".join(lines) + "\n")
