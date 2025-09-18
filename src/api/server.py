from __future__ import annotations

import os
import time
from typing import Dict, Tuple

from fastapi import FastAPI
from pydantic import BaseModel, Field

from src.gen.model import DesignBounds, sample_designs
from src.sim.surrogate import predict_metrics
from src.eval.constraints import check_constraints
from src.opt.mobo import pareto_front

app = FastAPI(title="Mech-Syn (Rocket)", version="0.1.0")


class GenerateReq(BaseModel):
    seed: int = 0
    n: int = Field(8, ge=1, le=64)
    bounds: Dict[str, Tuple[float, float]] = {
        "Pc": (5.0e6, 8.0e6),
        "throat_D": (0.03, 0.06),
        "area_ratio": (5.0, 20.0),
    }
    goals: Dict[str, str] = {"Thrust": ">=120000", "Isp": ">=300"}


@app.get("/health")
def health() -> Dict[str, str]:
    return {
        "status": "ok",
        "device": os.environ.get("OV_DEVICE", "AUTO"),
        "sim_xml": os.environ.get("OV_SIM_XML", ""),
        "gen_xml": os.environ.get("OV_GEN_XML", ""),
        "fake": os.environ.get("ALLOW_FAKE_GEN", "1"),
    }


@app.post("/v1/generate")
def generate(req: GenerateReq) -> Dict[str, object]:
    t0 = time.time()
    bounds = DesignBounds(**req.bounds)
    designs = sample_designs(bounds, n=req.n, seed=req.seed)
    preds = [predict_metrics(d) for d in designs]
    feas = [check_constraints(d, p) for d, p in zip(designs, preds)]
    records = [
        {
            "design": d,
            "pred": p,
            "feasible": f["feasible"],
            "margins": f["margins"],
        }
        for d, p, f in zip(designs, preds, feas)
    ]
    pareto = pareto_front(records)
    return {
        "candidates": records,
        "pareto": pareto,
        "elapsed_ms": int((time.time() - t0) * 1000),
    }
