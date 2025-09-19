from __future__ import annotations

from typing import Optional

from fastapi import FastAPI
from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel

from catalog.pencil_wrap import PENCIL_TYPES, pencil_optimize
from catalog.rocket_wrap import ROCKET_TYPES, rocket_optimize

app = FastAPI(title="Engine Catalog API")


class RocketOptions(BaseModel):
    type: str
    samples: Optional[int] = 256
    topk: Optional[int] = 16
    seed: Optional[int] = 123
    pa_kpa: Optional[float] = 101.325


class PencilOptions(BaseModel):
    type: str
    samples: Optional[int] = 256
    topk: Optional[int] = 16
    seed: Optional[int] = 123
    M0: Optional[float] = None
    alt_m: Optional[float] = None


@app.get("/catalog/health")
def health():
    return {"status": "ok"}


@app.get("/catalog/keys")
def keys():
    return {"rocket": list(ROCKET_TYPES.keys()), "pencil": list(PENCIL_TYPES.keys())}


@app.post("/catalog/rocket/optimize")
def catalog_rocket(req: RocketOptions):
    return {
        "type": req.type,
        "top": rocket_optimize(req.type, samples=req.samples, topk=req.topk, seed=req.seed, pa_kpa=req.pa_kpa),
    }


@app.post("/catalog/pencil/optimize")
def catalog_pencil(req: PencilOptions):
    return {
        "type": req.type,
        "top": pencil_optimize(req.type, samples=req.samples, topk=req.topk, seed=req.seed, M0=req.M0, alt_m=req.alt_m),
    }
