"""Prometheus style metrics with latency histogram buckets."""

from __future__ import annotations

import time

from fastapi import FastAPI, Request
from starlette.responses import PlainTextResponse


BUCKETS_MS = [5, 10, 20, 50, 100, 200, 500, 1000, 2000]


app = FastAPI(title="Metrics2")

_counts = {bucket: 0 for bucket in BUCKETS_MS}
_overflow = 0
_total = 0
_errors = 0
_start_time = time.time()


@app.middleware("http")
async def track_latency(request: Request, call_next):  # type: ignore[override]
    global _total, _errors, _overflow

    start = time.perf_counter()
    try:
        response = await call_next(request)
        return response
    except Exception:
        _errors += 1
        raise
    finally:
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        _total += 1
        for bucket in BUCKETS_MS:
            if elapsed_ms <= bucket:
                _counts[bucket] += 1
                break
        else:
            _overflow += 1


@app.get("/metrics")
def metrics() -> PlainTextResponse:
    lines = ["# TYPE bp_requests counter", f"bp_requests_total {_total}"]
    lines.append("# TYPE bp_errors counter")
    lines.append(f"bp_errors_total {_errors}")
    lines.append("# TYPE bp_latency histogram")

    cumulative = 0
    for bucket in BUCKETS_MS:
        cumulative += _counts[bucket]
        lines.append(f'bp_latency_bucket{{le="{bucket}"}} {cumulative}')
    lines.append(f'bp_latency_bucket{{le="+Inf"}} {cumulative + _overflow}')
    lines.append(f"bp_latency_count {_total}")
    lines.append(f"bp_uptime_seconds {int(time.time() - _start_time)}")

    return PlainTextResponse("\n".join(lines) + "\n")
