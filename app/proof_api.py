"""FastAPI entrypoint that runs a proof-of-concept experiment flow."""

from __future__ import annotations

import json
import os
import random
import time
import datetime as dt
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import FastAPI
from pydantic import BaseModel

try:
    from rocket.pipeline import RocketPipeline
    HAVE_ROCKET = True
except Exception:  # pragma: no cover - optional dependency
    HAVE_ROCKET = False

from blueprint.pipeline import Pipeline
from proof.logger import JsonlWriter, jsonl_to_csv

app = FastAPI(title="Blueprint Proof API")


class RunReq(BaseModel):
    mode: str = "rocket"
    samples: int = 256
    topk: int = 16
    noise: float = 0.03
    seed: Optional[int] = 123


def _now_id() -> str:
    return dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H-%M-%S")


def _exp_dir(run_id: str) -> Path:
    path = Path("data/experiments") / run_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def _summarize(pairs: List[tuple[float, float]]) -> Dict[str, float]:
    if not pairs:
        return {"rmse": float("nan"), "corr": float("nan")}

    import numpy as np

    data = np.asarray(pairs, dtype=float)
    rmse = float(np.sqrt(np.mean((data[:, 0] - data[:, 1]) ** 2)))
    if data.shape[0] < 2:
        corr = float("nan")
    else:
        corr = float(np.corrcoef(data[:, 0], data[:, 1])[0, 1])
    return {"rmse": rmse, "corr": corr}


@app.post("/proof/run_demo")
def run_demo(req: RunReq):
    run_id = _now_id()
    outdir = _exp_dir(run_id)
    random.seed(req.seed)
    started = time.perf_counter()

    if req.mode == "rocket" and HAVE_ROCKET:
        top = RocketPipeline().optimize(samples=req.samples, topk=req.topk, pa_kpa=101.325, seed=req.seed)
        designs = [item["design"] for item in top]
        preds = [
            {"score": item["score"], "Isp_s": item["Isp_s"], "F_N": item["F_N"]}
            for item in top
        ]
    else:
        pipeline = Pipeline(fake=os.getenv("BLUEPRINT_FAKE", "0") == "1")
        candidates = pipeline.generate(req.samples)
        scores = pipeline.predict(candidates)
        paired = sorted(zip(candidates, scores), key=lambda pair: pair[1], reverse=True)[: req.topk]
        designs = [design for design, _ in paired]
        preds = [{"score": float(score)} for _, score in paired]

    design_writer = JsonlWriter(outdir / "designs.jsonl")
    pred_writer = JsonlWriter(outdir / "predictions.jsonl")
    meas_writer = JsonlWriter(outdir / "measurements.jsonl")

    score_pairs: List[tuple[float, float]] = []
    for idx, (design, pred) in enumerate(zip(designs, preds)):
        design_writer.write({"run_id": run_id, "design_id": idx, "design": design})
        pred_writer.write({"run_id": run_id, "design_id": idx, "pred": pred})

        measurement: Dict[str, float] = {}
        for key, value in pred.items():
            mean = float(value)
            sigma = abs(mean) * req.noise
            epsilon = random.gauss(0.0, sigma)
            bias = 0.005 * mean
            measurement[key] = mean + epsilon - bias

        meas_writer.write(
            {
                "run_id": run_id,
                "design_id": idx,
                "meas": measurement,
                "ts": dt.datetime.now(dt.UTC).isoformat().replace("+00:00", "Z"),
            }
        )

        if "score" in pred and "score" in measurement:
            score_pairs.append((pred["score"], measurement["score"]))

    design_writer.close()
    pred_writer.close()
    meas_writer.close()

    jsonl_to_csv(outdir / "designs.jsonl", outdir / "designs.csv")
    jsonl_to_csv(outdir / "predictions.jsonl", outdir / "predictions.csv")
    jsonl_to_csv(outdir / "measurements.jsonl", outdir / "measurements.csv")

    summary = _summarize(score_pairs)
    meta = {
        "run_id": run_id,
        "mode": req.mode,
        "samples": req.samples,
        "topk": req.topk,
        "noise": req.noise,
        "seed": req.seed,
        "device": "CPU/NPU-auto",
    }
    (outdir / "run_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "ok": True,
        "run_id": run_id,
        "dir": str(outdir),
        "summary": summary,
        "count": len(designs),
        "elapsed_ms": int((time.perf_counter() - started) * 1000),
    }
