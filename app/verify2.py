"""Strict validation API that enforces parameter bounds before evaluation."""

from __future__ import annotations

from typing import Optional

from fastapi import Depends, FastAPI
from pydantic import BaseModel, ConfigDict, Field

from app.bootstrap import api_auth_dep, attach_common
from pencil.evaluator import evaluate_batch as evaluate_pencil
from rocket.evaluator import evaluate_batch as evaluate_rocket

app = attach_common(FastAPI(title="Verify2 API"))
AuthDep = api_auth_dep()


class RocketDesign(BaseModel):
    """Rocket design with strict bounds mirroring the sampling domain."""

    model_config = ConfigDict(extra="forbid")

    Pc_MPa: float = Field(ge=3.0, le=15.0)
    Tc_K: float = Field(ge=2400.0, le=4000.0)
    gamma: float = Field(ge=1.10, le=1.35)
    R: float = Field(ge=250.0, le=420.0)
    rt_mm: float = Field(ge=8.0, le=40.0)
    eps: float = Field(ge=4.0, le=40.0)
    spike_deg: float = Field(ge=5.0, le=25.0)
    film_frac: float = Field(ge=0.0, le=0.2)
    cool_frac: float = Field(ge=0.04, le=0.25)
    ch_d_mm: float = Field(ge=1.0, le=4.0)
    ch_n: int = Field(ge=40, le=240)
    pa_kpa: Optional[float] = Field(default=101.325, ge=0.0, le=200.0)


class PencilDesign(BaseModel):
    """Pencil (turbofan) design with tight validation ranges."""

    model_config = ConfigDict(extra="forbid")

    M0: float = Field(ge=0.0, le=2.5)
    alt_m: float = Field(ge=0.0, le=20_000.0)
    BPR: float = Field(ge=0.05, le=2.5)
    PRc: float = Field(ge=8.0, le=40.0)
    PRf: float = Field(ge=1.1, le=2.2)
    eta_c: float = Field(ge=0.7, le=1.0)
    eta_f: float = Field(ge=0.7, le=1.0)
    eta_t: float = Field(ge=0.7, le=1.0)
    eta_m: float = Field(ge=0.9, le=1.0)
    pi_d: float = Field(ge=0.7, le=1.0)
    pi_b: float = Field(ge=0.8, le=1.0)
    Tt4: float = Field(ge=1200.0, le=2300.0)
    m_core: float = Field(ge=5.0, le=60.0)


@app.get("/verify2/health")
def health() -> dict[str, object]:
    return {"status": "ok", "strict": True}


@app.post("/verify2/rocket")
def verify2_rocket(design: RocketDesign, _: None = Depends(AuthDep)) -> dict:
    pa = 101.325 if design.pa_kpa is None else float(design.pa_kpa)
    return evaluate_rocket([design.model_dump()], pa_kpa=pa)[0]


@app.post("/verify2/pencil")
def verify2_pencil(design: PencilDesign, _: None = Depends(AuthDep)) -> dict:
    return evaluate_pencil([design.model_dump()])[0]

