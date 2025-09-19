from __future__ import annotations

import requests
from fastapi import FastAPI

app = FastAPI(title="Aggregate Health")

TARGETS = [
    ("moo", "http://127.0.0.1:9007/moo/health"),
    ("moo2", "http://127.0.0.1:9015/moo2/health"),
    ("moo3", "http://127.0.0.1:9019/moo3/health"),
    ("assembly", "http://127.0.0.1:9005/assembly/health"),
    ("verify2", "http://127.0.0.1:9016/verify2/health"),
    ("metrics2", "http://127.0.0.1:9020/metrics"),
]


@app.get("/aggregate/health")
def health():
    results = []
    for name, url in TARGETS:
        ok = True
        try:
            response = requests.get(url, timeout=2)
            ok = response.status_code == 200
        except Exception:
            ok = False
        results.append({"name": name, "ok": bool(ok), "url": url})
    overall = all(item["ok"] for item in results) if results else False
    return {"ok": overall, "services": results}
