from __future__ import annotations

import random
from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel

from app.bootstrap import attach_common
from moo.constraints import pencil_violation, rocket_violation
from moo.nsga2 import nsga2
from pencil.evaluator import evaluate_batch as pencil_eval
from pencil.sampling import sample_lhs as pencil_sample_lhs
from rocket.evaluator import evaluate_batch as rocket_eval
from rocket.sampling import sample_lhs as rocket_sample_lhs

app = attach_common(FastAPI(title="MOO v3 (NSGA-II + Constraints)"))


class RocketRequest(BaseModel):
    samples: Optional[int] = 128
    generations: Optional[int] = 16
    seed: Optional[int] = 123
    pa_kpa: Optional[float] = 101.325
    topk: Optional[int] = 16


class PencilRequest(BaseModel):
    samples: Optional[int] = 128
    generations: Optional[int] = 16
    seed: Optional[int] = 123
    M0: Optional[float] = None
    alt_m: Optional[float] = None
    topk: Optional[int] = 16


@app.get("/moo3/health")
def health():
    return {"status": "ok", "algo": "nsga2", "constraints": "Deb(proxy)"}


@app.post("/moo3/rocket")
def moo3_rocket(req: RocketRequest):
    rng = random.Random(req.seed)
    init = rocket_sample_lhs(req.samples, seed=req.seed)

    def objective(design):
        metrics = rocket_eval([design], pa_kpa=req.pa_kpa)[0]
        violation = rocket_violation(metrics)
        return (
            violation,
            metrics["q_bartz_W_m2"],
            metrics["dp_regen_Pa"],
            -metrics["Isp_s"],
        )

    population = nsga2(
        init,
        objective,
        minimize=[True, True, True, True],
        rng=rng,
        generations=req.generations,
        pop_size=req.samples,
    )
    metrics = rocket_eval(population, pa_kpa=req.pa_kpa)
    metrics = [metric for metric in metrics if rocket_violation(metric) <= 1e-6]
    metrics.sort(key=lambda item: (-item["Isp_s"], item["q_bartz_W_m2"], item["dp_regen_Pa"]))
    return {"top": metrics[: req.topk]}


@app.post("/moo3/pencil")
def moo3_pencil(req: PencilRequest):
    rng = random.Random(req.seed)
    init = pencil_sample_lhs(req.samples, seed=req.seed, M0_fixed=req.M0, alt_fixed=req.alt_m)

    def objective(design):
        metrics = pencil_eval([design])[0]
        violation = pencil_violation(metrics)
        return (
            violation,
            metrics["TSFC_kg_per_Ns"],
            metrics["f_fuel"],
            -metrics["spec_thrust_N_per_kgps"],
        )

    population = nsga2(
        init,
        objective,
        minimize=[True, True, True, True],
        rng=rng,
        generations=req.generations,
        pop_size=req.samples,
    )
    metrics = pencil_eval(population)
    metrics = [metric for metric in metrics if pencil_violation(metric) <= 1e-6]
    metrics.sort(
        key=lambda item: (
            -item["spec_thrust_N_per_kgps"],
            item["TSFC_kg_per_Ns"],
            item.get("f_fuel", 1e9),
        )
    )
    return {"top": metrics[: req.topk]}
