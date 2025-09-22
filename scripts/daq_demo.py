"""Emit synthetic DAQ readings for rocket or pencil modes."""

from __future__ import annotations

import argparse

import json


from pencil.pipeline import PencilPipeline
from proof.daq import read_measurement
from rocket.pipeline import RocketPipeline


def _rocket_predictions(count: int):
    pipeline = RocketPipeline()
    candidates = pipeline.optimize(samples=128, topk=count)
    return [
        {"score": item["score"], "Isp_s": item["Isp_s"], "F_N": item["F_N"]}
        for item in candidates
    ]


def _pencil_predictions(count: int):
    pipeline = PencilPipeline()
    candidates = pipeline.optimize(samples=128, topk=count, M0=0.9, alt_m=2000.0)
    return [
        {"score": item["score"], "F_N": item["F_N"], "TSFC": item["TSFC_kg_per_Ns"]}
        for item in candidates
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["rocket", "pencil"], default="rocket")
    parser.add_argument("--n", type=int, default=5)
    args = parser.parse_args()

    if args.mode == "rocket":
        predictions = _rocket_predictions(args.n)
    else:
        predictions = _pencil_predictions(args.n)

    rows = []
    for idx, pred in enumerate(predictions):
        meas = read_measurement(pred, noise=0.03)
        rows.append({"id": idx, "pred": pred, "meas": meas})

    print(json.dumps(rows, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
