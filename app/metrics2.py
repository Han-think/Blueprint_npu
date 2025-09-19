from __future__ import annotations

import time

from fastapi import FastAPI, Request
from starlette.responses import PlainTextResponse

_BUCKETS = [5, 10, 20, 50, 100, 200, 500, 1000, 2000]
_counts = {bucket: 0 for bucket in _BUCKETS}
_inf = 0
_total = 0
_errors = 0
_uptime = time.time()

app = FastAPI(title="Metrics2")


@app.middleware("http")
async def latency_middleware(request: Request, call_next):
    global _total, _errors, _inf
    start = time.perf_counter()
    try:
        response = await call_next(request)
        return response
    except Exception:
        _errors += 1
        raise
    finally:
        dt_ms = (time.perf_counter() - start) * 1000.0
        _total += 1
        placed = False
        for bucket in _BUCKETS:
            if dt_ms <= bucket:
                _counts[bucket] += 1
                placed = True
                break
        if not placed:
            _inf += 1


@app.get("/metrics")
def metrics():
    lines = ["# TYPE bp_requests counter", f"bp_requests_total {_total}"]
    lines.extend(["# TYPE bp_errors counter", f"bp_errors_total {_errors}"])
    lines.append("# TYPE bp_latency histogram")
    cumulative = 0
    for bucket in _BUCKETS:
        cumulative += _counts[bucket]
        lines.append(f'bp_latency_bucket{{le="{bucket}"}} {cumulative}')
    lines.append(f'bp_latency_bucket{{le="+Inf"}} {cumulative + _inf}')
    lines.append(f"bp_latency_count {_total}")
    lines.append(f"bp_uptime_seconds {int(time.time() - _uptime)}")
    return PlainTextResponse("\n".join(lines) + "\n")
