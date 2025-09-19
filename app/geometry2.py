from __future__ import annotations

from fastapi import FastAPI

app = FastAPI(title="Geometry2 API")


@app.get("/geometry2/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
