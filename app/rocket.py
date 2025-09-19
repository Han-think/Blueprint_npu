"""FastAPI application exposing the rocket optimization pipeline."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import FastAPI
from pydantic import BaseModel

from rocket.pipeline import RocketPipeline


app = FastAPI(title="Rocket Blueprint API")
pipe = RocketPipeline()


class OptReq(BaseModel):
    """Request body for the optimization endpoint."""

    samples: Optional[int] = 256
    topk: Optional[int] = 16
    pa_kpa: Optional[float] = 101.325
    seed: Optional[int] = None


@app.get("/rocket/health")
def health() -> Dict[str, Any]:
    """Simple health endpoint for smoke checks."""

    return {"status": "ok", "device": "CPU", "mode": "rocket"}


@app.post("/rocket/optimize")
def optimize(req: OptReq) -> Dict[str, List[Dict[str, Any]]]:
    """Run the rocket optimization pipeline and return top designs."""

    res = pipe.optimize(
        samples=req.samples,
        topk=req.topk,
        pa_kpa=req.pa_kpa,
        seed=req.seed,
    )
    return {"top": res}

