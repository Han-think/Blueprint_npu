from __future__ import annotations

import datetime as dt
import json
import os
import datetime as dt
import json
import os
import random
from pathlib import Path
from typing import Any, Dict, List, Tuple

from fastapi import FastAPI
from pydantic import BaseModel

from blueprint.pipeline import Pipeline
from proof.logger import JsonlWriter, jsonl_to_csv

try:
    from rocket.pipeline import RocketPipeline

    HAVE_ROCKET = True
except Exception:  # pragma: no cover - optional dependency
    HAVE_ROCKET = False

app = FastAPI(title="Blueprint Proof API")


class RunRequest(BaseModel):
    mode: str = "rocket"
    samples: int = 256
    topk: int = 16
    noise: float = 0.03
    seed: int | None = 123


def _run_id() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")


def _exp_dir(run_id: str) -> Path:
    directory = Path("data/experiments") / run_id
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _summarise(pairs: List[Tuple[float, float]]) -> Dict[str, float]:
    if not pairs:
        return {"rmse": float("nan"), "corr": float("nan")}
    import numpy as np

    arr = np.asarray(pairs, dtype=float)
    rmse = float(np.sqrt(np.mean((arr[:, 0] - arr[:, 1]) ** 2)))
    corr = float(np.corrcoef(arr[:, 0], arr[:, 1])[0, 1]) if len(arr) >= 2 else float("nan")
    return {"rmse": rmse, "corr": corr}


@app.post("/proof/run_demo")
def run_demo(req: RunRequest):
    run_id = _run_id()
    outdir = _exp_dir(run_id)
    random.seed(req.seed)

    if req.mode == "rocket" and HAVE_ROCKET:
        pipeline = RocketPipeline()
        top = pipeline.optimize(samples=req.samples, topk=req.topk, pa_kpa=101.325, seed=req.seed)
        designs = [item["design"] for item in top]
        predictions = [{"score": item["score"], "Isp_s": item["Isp_s"], "F_N": item["F_N"]} for item in top]
    else:
        pipeline = Pipeline(fake=os.getenv("BLUEPRINT_FAKE", "0") == "1")
        generated = pipeline.generate(req.samples)
        predicted = pipeline.predict(generated)
        ranked = sorted(zip(generated, predicted), key=lambda row: row[1], reverse=True)[: req.topk]
        designs = [design for design, _ in ranked]
        predictions = [{"score": float(score)} for _, score in ranked]

    design_writer = JsonlWriter(outdir / "designs.jsonl")
    pred_writer = JsonlWriter(outdir / "predictions.jsonl")
    meas_writer = JsonlWriter(outdir / "measurements.jsonl")

    pairs: List[Tuple[float, float]] = []
    for idx, (design, pred) in enumerate(zip(designs, predictions)):
        design_writer.write({"run_id": run_id, "design_id": idx, "design": design})
        pred_writer.write({"run_id": run_id, "design_id": idx, "pred": pred})
        measurement: Dict[str, Any] = {}
        for key, value in pred.items():
            mu = float(value)
            sigma = abs(mu) * req.noise
            noise = random.gauss(0.0, sigma)
            bias = 0.005 * mu
            measurement[key] = mu + noise - bias
        meas_writer.write(
            {
                "run_id": run_id,
                "design_id": idx,
                "meas": measurement,
                "ts": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
            }
        )
        if "score" in pred and "score" in measurement:
            pairs.append((pred["score"], measurement["score"]))

    design_writer.close()
    pred_writer.close()
    meas_writer.close()

    jsonl_to_csv(outdir / "designs.jsonl", outdir / "designs.csv")
    jsonl_to_csv(outdir / "predictions.jsonl", outdir / "predictions.csv")
    jsonl_to_csv(outdir / "measurements.jsonl", outdir / "measurements.csv")

    summary = _summarise(pairs)
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

    return {"ok": True, "run_id": run_id, "dir": str(outdir), "summary": summary, "count": len(designs)}
