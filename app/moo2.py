from __future__ import annotations

import random
import random
from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel

from moo.nsga2 import nsga2
from pencil.evaluator import evaluate_batch as pencil_eval
from pencil.sampling import sample_lhs as pencil_sample_lhs
from rocket.evaluator import evaluate_batch as rocket_eval
from rocket.sampling import sample_lhs as rocket_sample_lhs

app = FastAPI(title="MOO v2 (NSGA-II)")


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


@app.get("/moo2/health")
def health():
    return {"status": "ok", "algo": "nsga2"}


@app.post("/moo2/rocket")
def moo2_rocket(req: RocketRequest):
    rng = random.Random(req.seed)
    init = rocket_sample_lhs(req.samples, seed=req.seed)

    def objective(design):
        metric = rocket_eval([design], pa_kpa=req.pa_kpa)[0]
        return (-metric["Isp_s"], metric["q_bartz_W_m2"], metric["dp_regen_Pa"])

    population = nsga2(init, objective, minimize=[True, True, True], rng=rng, generations=req.generations, pop_size=req.samples)
    metrics = rocket_eval(population, pa_kpa=req.pa_kpa)
    metrics = [m for m in metrics if m["ok"]]
    metrics.sort(key=lambda item: (-item["Isp_s"], item["q_bartz_W_m2"], item["dp_regen_Pa"]))
    return {"top": metrics[: req.topk]}


@app.post("/moo2/pencil")
def moo2_pencil(req: PencilRequest):
    rng = random.Random(req.seed)
    init = pencil_sample_lhs(req.samples, seed=req.seed, M0_fixed=req.M0, alt_fixed=req.alt_m)

    def objective(design):
        metric = pencil_eval([design])[0]
        return (-metric["spec_thrust_N_per_kgps"], metric["TSFC_kg_per_Ns"], metric["f_fuel"])

    population = nsga2(init, objective, minimize=[True, True, True], rng=rng, generations=req.generations, pop_size=req.samples)
    metrics = pencil_eval(population)
    metrics = [m for m in metrics if m["ok"]]
    metrics.sort(
        key=lambda item: (
            -item["spec_thrust_N_per_kgps"],
            item["TSFC_kg_per_Ns"],
            item["f_fuel"],
        )
    )
    return {"top": metrics[: req.topk]}
