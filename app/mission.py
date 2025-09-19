from __future__ import annotations

from typing import List

from fastapi import Depends, FastAPI
from pydantic import BaseModel

from app.security import require_api_key

app = FastAPI(title="Mission API")


class MissionLeg(BaseModel):
    type: str
    duration_s: float


class MissionRequest(BaseModel):
    legs: List[MissionLeg]


@app.get("/mission/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/mission/run")
def run_mission(req: MissionRequest, _: None = Depends(require_api_key)) -> dict[str, int]:
    return {"legs": len(req.legs)}
