"""Aggregate health endpoint to poll multiple services."""

from __future__ import annotations

from typing import Iterable, List, Tuple

import requests
from fastapi import FastAPI


app = FastAPI(title="Aggregate Health")


TARGETS: List[Tuple[str, str]] = [
    ("moo", "http://127.0.0.1:9007/moo/health"),
    ("moo2", "http://127.0.0.1:9015/moo2/health"),
    ("moo3", "http://127.0.0.1:9019/moo3/health"),
    ("assembly", "http://127.0.0.1:9005/assembly/health"),
    ("verify2", "http://127.0.0.1:9016/verify2/health"),
    ("metrics2", "http://127.0.0.1:9020/metrics"),
]


def _check_targets(targets: Iterable[Tuple[str, str]]) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for name, url in targets:
        ok = True
        try:
            response = requests.get(url, timeout=2.0)
            ok = response.status_code == 200
        except Exception:
            ok = False
        results.append({"name": name, "url": url, "ok": bool(ok)})
    return results


@app.get("/aggregate/health")
def health() -> dict[str, object]:
    services = _check_targets(TARGETS)
    overall = all(item["ok"] for item in services) if services else False
    return {"ok": overall, "services": services}
