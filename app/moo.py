"""FastAPI service exposing multi-objective optimization endpoints."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import FastAPI
from pydantic import BaseModel

from moo.pareto import pareto_front
from pencil.evaluator import evaluate_batch as pencil_eval
from pencil.generator import sample as pencil_sample
from rocket.evaluator import evaluate_batch as rocket_eval
from rocket.generator import sample as rocket_sample

app = FastAPI(title="MOO API")


class RocketRequest(BaseModel):
    samples: Optional[int] = 256
    topk: Optional[int] = 16
    seed: Optional[int] = 123
    pa_kpa: Optional[float] = 101.325


class PencilRequest(BaseModel):
    samples: Optional[int] = 256
    topk: Optional[int] = 16
    seed: Optional[int] = 123
    M0: Optional[float] = None
    alt_m: Optional[float] = None


@app.get("/moo/health")
def health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "objectives": {
            "rocket": ["Isp(max)", "q_bartz(min)", "dp_regen(min)"],
            "pencil": ["spec_thrust(max)", "TSFC(min)", "f_fuel(min)"],
        },
    }


@app.post("/moo/rocket")
def moo_rocket(req: RocketRequest) -> Dict[str, Any]:
    designs = rocket_sample(req.samples, seed=req.seed)
    metrics = [m for m in rocket_eval(designs, pa_kpa=req.pa_kpa) if m["ok"]]
    if not metrics:
        return {"top": []}

    objectives = [
        (-m["Isp_s"], m["q_bartz_W_m2"], m["dp_regen_Pa"]) for m in metrics
    ]
    front_idx = pareto_front(objectives, minimize=[True, True, True])
    front = [metrics[i] for i in front_idx]
    front.sort(key=lambda m: (-m["Isp_s"], m["q_bartz_W_m2"], m["dp_regen_Pa"]))
    return {"top": front[: req.topk]}


@app.post("/moo/pencil")
def moo_pencil(req: PencilRequest) -> Dict[str, Any]:
    designs = pencil_sample(req.samples, seed=req.seed, M0_fixed=req.M0, alt_fixed=req.alt_m)
    metrics = [m for m in pencil_eval(designs) if m["ok"]]
    if not metrics:
        return {"top": []}

    objectives = [
        (-m["spec_thrust_N_per_kgps"], m["TSFC_kg_per_Ns"], m["f_fuel"]) for m in metrics
    ]
    front_idx = pareto_front(objectives, minimize=[True, True, True])
    front = [metrics[i] for i in front_idx]
    front.sort(
        key=lambda m: (
            -m["spec_thrust_N_per_kgps"],
            m["TSFC_kg_per_Ns"],
            m["f_fuel"],
        )
    )
    return {"top": front[: req.topk]}
