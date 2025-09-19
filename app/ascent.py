from __future__ import annotations

from fastapi import Depends, FastAPI

from app.security import require_api_key

app = FastAPI(title="Ascent API")


@app.get("/ascent/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/ascent/ping", dependencies=[Depends(require_api_key)])
def ping() -> dict[str, str]:
    return {"message": "ascent ack"}
