"""FastAPI application exposing the pencil (turbofan) optimization pipeline."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import FastAPI
from pydantic import BaseModel

from pencil.pipeline import PencilPipeline


app = FastAPI(title="Pencil Engine API")
pipe = PencilPipeline()


class OptReq(BaseModel):
    """Request body for the pencil optimization endpoint."""

    samples: Optional[int] = 256
    topk: Optional[int] = 16
    seed: Optional[int] = None
    M0: Optional[float] = None
    alt_m: Optional[float] = None


@app.get("/pencil/health")
def health() -> Dict[str, Any]:
    """Return a simple payload for smoke tests."""

    return {"status": "ok", "mode": "pencil"}


@app.post("/pencil/optimize")
def optimize(req: OptReq) -> Dict[str, List[Dict[str, Any]]]:
    """Run the pencil pipeline and return the best designs."""

    res = pipe.optimize(
        samples=req.samples,
        topk=req.topk,
        seed=req.seed,
        M0=req.M0,
        alt_m=req.alt_m,
    )
    return {"top": res}
