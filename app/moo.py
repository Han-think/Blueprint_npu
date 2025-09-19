from __future__ import annotations

import random
from typing import Optional

import random
from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel

from moo.ga import nsga_lite
from moo.pareto import pareto_front
from pencil.evaluator import evaluate_batch as pencil_eval
from pencil.generator import sample as pencil_sample_random
from pencil.sampling import sample_lhs as pencil_sample_lhs
from rocket.evaluator import evaluate_batch as rocket_eval
from rocket.generator import sample as rocket_sample_random
from rocket.sampling import sample_lhs as rocket_sample_lhs

app = FastAPI(title="MOO API")


class RocketRequest(BaseModel):
    samples: Optional[int] = 256
    topk: Optional[int] = 16
    seed: Optional[int] = 123
    pa_kpa: Optional[float] = 101.325
    method: Optional[str] = "random"
    generations: Optional[int] = 10


class PencilRequest(BaseModel):
    samples: Optional[int] = 256
    topk: Optional[int] = 16
    seed: Optional[int] = 123
    M0: Optional[float] = None
    alt_m: Optional[float] = None
    method: Optional[str] = "random"
    generations: Optional[int] = 10


@app.get("/moo/health")
def health():
    return {
        "status": "ok",
        "objectives": {
            "rocket": ["Isp(max)", "q_bartz(min)", "dp_regen(min)"],
            "pencil": ["spec_thrust(max)", "TSFC(min)", "fuel_frac(min)"],
        },
        "methods": ["random", "lhs", "ga"],
    }


@app.post("/moo/rocket")
def moo_rocket(req: RocketRequest):
    rng = random.Random(req.seed)
    if req.method == "lhs":
        designs = rocket_sample_lhs(req.samples, seed=req.seed)
    elif req.method == "ga":
        init = rocket_sample_lhs(req.samples // 2, seed=req.seed)

        def objective(design):
            metrics = rocket_eval([design], pa_kpa=req.pa_kpa)[0]
            return (-metrics["Isp_s"], metrics["q_bartz_W_m2"], metrics["dp_regen_Pa"])

        pop = nsga_lite(init, objective, minimize=[True, True, True], rng=rng, generations=req.generations)
        metrics = rocket_eval(pop, pa_kpa=req.pa_kpa)
        metrics = [m for m in metrics if m["ok"]]
        metrics.sort(key=lambda item: (-item["Isp_s"], item["q_bartz_W_m2"], item["dp_regen_Pa"]))
        return {"top": metrics[: req.topk]}
    else:
        designs = rocket_sample_random(req.samples, seed=req.seed)
    metrics = rocket_eval(designs, pa_kpa=req.pa_kpa)
    metrics = [m for m in metrics if m["ok"]]
    if not metrics:
        return {"top": []}
    objectives = [(-m["Isp_s"], m["q_bartz_W_m2"], m["dp_regen_Pa"]) for m in metrics]
    indices = pareto_front(objectives, minimize=[True, True, True])
    front = [metrics[i] for i in indices]
    front.sort(key=lambda item: (-item["Isp_s"], item["q_bartz_W_m2"], item["dp_regen_Pa"]))
    return {"top": front[: req.topk]}


@app.post("/moo/pencil")
def moo_pencil(req: PencilRequest):
    rng = random.Random(req.seed)
    if req.method == "lhs":
        designs = pencil_sample_lhs(req.samples, seed=req.seed, M0_fixed=req.M0, alt_fixed=req.alt_m)
    elif req.method == "ga":
        init = pencil_sample_lhs(req.samples // 2, seed=req.seed, M0_fixed=req.M0, alt_fixed=req.alt_m)

        def objective(design):
            metrics = pencil_eval([design])[0]
            return (-metrics["spec_thrust_N_per_kgps"], metrics["TSFC_kg_per_Ns"], metrics["f_fuel"])

        pop = nsga_lite(init, objective, minimize=[True, True, True], rng=rng, generations=req.generations)
        metrics = pencil_eval(pop)
        metrics = [m for m in metrics if m["ok"]]
        metrics.sort(
            key=lambda item: (
                -item["spec_thrust_N_per_kgps"],
                item["TSFC_kg_per_Ns"],
                item["f_fuel"],
            )
        )
        return {"top": metrics[: req.topk]}
    else:
        designs = pencil_sample_random(req.samples, seed=req.seed, M0_fixed=req.M0, alt_fixed=req.alt_m)
    metrics = pencil_eval(designs)
    metrics = [m for m in metrics if m["ok"]]
    if not metrics:
        return {"top": []}
    objectives = [(-m["spec_thrust_N_per_kgps"], m["TSFC_kg_per_Ns"], m["f_fuel"]) for m in metrics]
    indices = pareto_front(objectives, minimize=[True, True, True])
    front = [metrics[i] for i in indices]
    front.sort(
        key=lambda item: (
            -item["spec_thrust_N_per_kgps"],
            item["TSFC_kg_per_Ns"],
            item["f_fuel"],
        )
    )
    return {"top": front[: req.topk]}
