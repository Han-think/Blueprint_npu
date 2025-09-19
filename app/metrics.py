"""Minimal Prometheus-style metrics endpoint."""

from __future__ import annotations

from fastapi import FastAPI, Request
from starlette.responses import PlainTextResponse

app = FastAPI(title="Metrics")

_REQUEST_COUNT = 0
_ERROR_COUNT = 0


@app.middleware("http")
async def _record(request: Request, call_next):  # type: ignore[override]
    global _REQUEST_COUNT, _ERROR_COUNT
    _REQUEST_COUNT += 1
    try:
        response = await call_next(request)
    except Exception:  # pragma: no cover - bubble up but count failures
        _ERROR_COUNT += 1
        raise
    return response


@app.get("/metrics")
def metrics() -> PlainTextResponse:
    lines = [
        "# HELP bp_requests_total Total HTTP requests",
        "# TYPE bp_requests_total counter",
        f"bp_requests_total {_REQUEST_COUNT}",
        "# HELP bp_errors_total Total unhandled errors",
        "# TYPE bp_errors_total counter",
        f"bp_errors_total {_ERROR_COUNT}",
    ]
    return PlainTextResponse("\n".join(lines) + "\n")
