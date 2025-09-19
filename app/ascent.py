from __future__ import annotations

from fastapi import Depends, FastAPI
from pydantic import BaseModel

from app.security import require_api_key

app = FastAPI(title="Ascent API")


class AscentRequest(BaseModel):
    mass_kg: float = 1000.0


@app.get("/ascent/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/ascent/run")
def run(_: AscentRequest, __: None = Depends(require_api_key)) -> dict[str, float]:
    return {"max_altitude_m": 100.0}
