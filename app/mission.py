from __future__ import annotations

from fastapi import Depends, FastAPI

from app.security import require_api_key

app = FastAPI(title="Mission API")


@app.get("/mission/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/mission/ping", dependencies=[Depends(require_api_key)])
def ping() -> dict[str, str]:
    return {"message": "mission ack"}
