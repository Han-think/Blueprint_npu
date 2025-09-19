"""Combined rocket verification and material feasibility endpoint."""

from __future__ import annotations

from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel

from rocket.evaluator import evaluate_batch as evaluate_rocket
from rocket.material_check import evaluate_material

app = FastAPI(title="Verify+Material")


class RocketDesign(BaseModel):
    Pc_MPa: float
    Tc_K: float
    gamma: float
    R: float
    rt_mm: float
    eps: float
    spike_deg: float
    film_frac: float
    cool_frac: float
    ch_d_mm: float
    ch_n: int
    pa_kpa: Optional[float] = 101.325
    material: Optional[str] = "Inconel718"


@app.get("/verifym/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/verifym/rocket")
def verify_material(design: RocketDesign) -> dict:
    metrics = evaluate_rocket([design.model_dump()], pa_kpa=design.pa_kpa or 101.325)[0]
    material_report = evaluate_material(design.model_dump(), metrics, material=design.material or "Inconel718")
    return {"metric": metrics, "material": material_report}
