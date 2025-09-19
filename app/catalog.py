"""FastAPI application exposing cataloged rocket and pencil optimizers."""

from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional

from catalog.rocket_wrap import ROCKET_TYPES, rocket_optimize
from catalog.pencil_wrap import PENCIL_TYPES, pencil_optimize


app = FastAPI(title="Engine Catalog API")


class RocketOptimizeRequest(BaseModel):
    """Request body for rocket optimization calls."""

    type: str
    samples: Optional[int] = 256
    topk: Optional[int] = 16
    seed: Optional[int] = 123
    pa_kpa: Optional[float] = 101.325


class PencilOptimizeRequest(BaseModel):
    """Request body for pencil optimization calls."""

    type: str
    samples: Optional[int] = 256
    topk: Optional[int] = 16
    seed: Optional[int] = 123
    M0: Optional[float] = None
    alt_m: Optional[float] = None


@app.get("/catalog/health")
def health() -> dict[str, str]:
    """Simple service health indicator."""

    return {"status": "ok"}


@app.get("/catalog/keys")
def keys() -> dict[str, list[str]]:
    """Expose available rocket and pencil archetype keys."""

    return {
        "rocket": list(ROCKET_TYPES.keys()),
        "pencil": list(PENCIL_TYPES.keys()),
    }


@app.post("/catalog/rocket/optimize")
def catalog_rocket(req: RocketOptimizeRequest) -> dict[str, object]:
    """Run the requested rocket optimizer profile and return the top designs."""

    top = rocket_optimize(
        req.type,
        samples=req.samples,
        topk=req.topk,
        seed=req.seed,
        pa_kpa=req.pa_kpa,
    )
    return {"type": req.type, "top": top}


@app.post("/catalog/pencil/optimize")
def catalog_pencil(req: PencilOptimizeRequest) -> dict[str, object]:
    """Run the requested pencil optimizer profile and return the top designs."""

    top = pencil_optimize(
        req.type,
        samples=req.samples,
        topk=req.topk,
        seed=req.seed,
        M0=req.M0,
        alt_m=req.alt_m,
    )
    return {"type": req.type, "top": top}

