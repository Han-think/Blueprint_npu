"""Constraint-aware NSGA-II optimisation service."""

from __future__ import annotations

import random
from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel

from app.bootstrap import attach_common
from moo.constraints import pencil_violation, rocket_violation
from moo.nsga2 import nsga2
from pencil.evaluator import evaluate_batch as p_eval
from pencil.sampling import sample_lhs as p_sample_lhs
from rocket.evaluator import evaluate_batch as r_eval
from rocket.sampling import sample_lhs as r_sample_lhs


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
def health() -> dict[str, object]:
    return {"status": "ok", "algo": "nsga2", "constraints": "Deb(proxy)"}


@app.post("/moo3/rocket")
def moo3_rocket(req: RocketRequest) -> dict[str, object]:
    rng = random.Random(req.seed)
    initial = r_sample_lhs(req.samples, seed=req.seed)

    def objective(design: dict) -> tuple[float, float, float, float]:
        metric = r_eval([design], pa_kpa=req.pa_kpa)[0]
        violation = rocket_violation(metric)
        return (
            violation,
            metric["q_bartz_W_m2"],
            metric["dp_regen_Pa"],
            -metric["Isp_s"],
        )

    population = nsga2(
        initial,
        objective,
        minimize=[True, True, True, True],
        rng=rng,
        generations=req.generations,
        pop_size=req.samples,
    )
    metrics = r_eval(population, pa_kpa=req.pa_kpa)
    metrics = [m for m in metrics if rocket_violation(m) <= 1e-6]
    metrics.sort(key=lambda m: (-m["Isp_s"], m["q_bartz_W_m2"], m["dp_regen_Pa"]))
    return {"top": metrics[: req.topk]}


@app.post("/moo3/pencil")
def moo3_pencil(req: PencilRequest) -> dict[str, object]:
    rng = random.Random(req.seed)
    initial = p_sample_lhs(req.samples, seed=req.seed, M0_fixed=req.M0, alt_fixed=req.alt_m)

    def objective(design: dict) -> tuple[float, float, float, float]:
        metric = p_eval([design])[0]
        violation = pencil_violation(metric)
        return (
            violation,
            metric["TSFC_kg_per_Ns"],
            metric.get("f_fuel", 1.0),
            -metric["spec_thrust_N_per_kgps"],
        )

    population = nsga2(
        initial,
        objective,
        minimize=[True, True, True, True],
        rng=rng,
        generations=req.generations,
        pop_size=req.samples,
    )
    metrics = p_eval(population)
    metrics = [m for m in metrics if pencil_violation(m) <= 1e-6]
    metrics.sort(
        key=lambda m: (
            -m["spec_thrust_N_per_kgps"],
            m["TSFC_kg_per_Ns"],
            m.get("f_fuel", 1e9),
        )
    )
    return {"top": metrics[: req.topk]}
