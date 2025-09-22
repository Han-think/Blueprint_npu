from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
import random


from moo.pareto import pareto_front
from moo.ga import nsga_lite
from rocket.generator import sample as rocket_sample_rand
from rocket.sampling import sample_lhs as rocket_sample_lhs
from rocket.evaluator import evaluate_batch as rocket_eval
from pencil.generator import sample as pencil_sample_rand
from pencil.sampling import sample_lhs as pencil_sample_lhs
from pencil.evaluator import evaluate_batch as pencil_eval

codex/initialize-npu-inference-template-ys4nnv
try:
    from app.middleware import SimpleLogger

    _WITH_MIDDLEWARE = True
except Exception:
    _WITH_MIDDLEWARE = False

app = FastAPI(title="MOO API")
if _WITH_MIDDLEWARE:
    app.add_middleware(SimpleLogger)

app = FastAPI(title="MOO API")
main


class RocketRequest(BaseModel):
    samples: Optional[int] = 256
    topk: Optional[int] = 16
    seed: Optional[int] = 123
    pa_kpa: Optional[float] = 101.325
    method: Optional[str] = "random"  # random|lhs|ga
    generations: Optional[int] = 10


class PencilRequest(BaseModel):
    samples: Optional[int] = 256
    topk: Optional[int] = 16
    seed: Optional[int] = 123
    M0: Optional[float] = None
    alt_m: Optional[float] = None
    method: Optional[str] = "random"  # random|lhs|ga
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
        seed_pop = rocket_sample_lhs(max(2, req.samples // 2), seed=req.seed)

        def obj_fn(design):
            metric = rocket_eval([design], pa_kpa=req.pa_kpa)[0]
            return (-metric["Isp_s"], metric["q_bartz_W_m2"], metric["dp_regen_Pa"])

        population = nsga_lite(
            seed_pop,
            obj_fn,
            minimize=[True, True, True],
            rng=rng,
            gens=req.generations,
        )
        metrics = rocket_eval(population, pa_kpa=req.pa_kpa)
        metrics = [m for m in metrics if m["ok"]]
        metrics.sort(key=lambda m: (-m["Isp_s"], m["q_bartz_W_m2"], m["dp_regen_Pa"]))
        return {"top": metrics[: req.topk]}
    else:
        designs = rocket_sample_rand(req.samples, seed=req.seed)

    metrics = [m for m in rocket_eval(designs, pa_kpa=req.pa_kpa) if m["ok"]]
    if not metrics:
        return {"top": []}

    objectives = [(-m["Isp_s"], m["q_bartz_W_m2"], m["dp_regen_Pa"]) for m in metrics]
    front_idx = pareto_front(objectives, minimize=[True, True, True])
    front = [metrics[i] for i in front_idx]
    front.sort(key=lambda m: (-m["Isp_s"], m["q_bartz_W_m2"], m["dp_regen_Pa"]))
    return {"top": front[: req.topk]}


@app.post("/moo/pencil")
def moo_pencil(req: PencilRequest):
    rng = random.Random(req.seed)

    if req.method == "lhs":
        designs = pencil_sample_lhs(
            req.samples, seed=req.seed, M0_fixed=req.M0, alt_fixed=req.alt_m
        )
    elif req.method == "ga":
        seed_pop = pencil_sample_lhs(
            max(2, req.samples // 2), seed=req.seed, M0_fixed=req.M0, alt_fixed=req.alt_m
        )

        def obj_fn(design):
            metric = pencil_eval([design])[0]
            return (
                -metric["spec_thrust_N_per_kgps"],
                metric["TSFC_kg_per_Ns"],
                metric["f_fuel"],
            )

        population = nsga_lite(
            seed_pop,
            obj_fn,
            minimize=[True, True, True],
            rng=rng,
            gens=req.generations,
        )
        metrics = pencil_eval(population)
        metrics = [m for m in metrics if m["ok"]]
        metrics.sort(
            key=lambda m: (
                -m["spec_thrust_N_per_kgps"],
                m["TSFC_kg_per_Ns"],
                m["f_fuel"],
            )
        )
        return {"top": metrics[: req.topk]}
    else:
        designs = pencil_sample_rand(
            req.samples, seed=req.seed, M0_fixed=req.M0, alt_fixed=req.alt_m
        )

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
