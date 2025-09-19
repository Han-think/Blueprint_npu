from __future__ import annotations

from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel

from rocket.evaluator import evaluate_batch as rocket_eval
from pencil.evaluator import evaluate_batch as pencil_eval

app = FastAPI(title="Verify API")


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


class PencilDesign(BaseModel):
    M0: float
    alt_m: float
    BPR: float
    PRc: float
    PRf: float
    eta_c: float
    eta_f: float
    eta_t: float
    eta_m: float
    pi_d: float
    pi_b: float
    Tt4: float
    m_core: float


@app.get("/verify/health")
def health():
    return {"status": "ok"}


@app.post("/verify/rocket")
def verify_rocket(design: RocketDesign):
    metric = rocket_eval([design.model_dump()], pa_kpa=design.pa_kpa or 101.325)[0]
    return metric


@app.post("/verify/pencil")
def verify_pencil(design: PencilDesign):
    metric = pencil_eval([design.model_dump()])[0]
    return metric
