"""Generate surrogate datasets for rocket and pencil evaluators."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Tuple

import numpy as np


def _rocket_dataset(samples: int, seed: int) -> Tuple[np.ndarray, np.ndarray, list[str], list[str]]:
    from rocket.evaluator import evaluate_batch
    from rocket.sampling import sample_lhs

    designs = sample_lhs(samples, seed=seed)
    metrics = evaluate_batch(designs)

    features = []
    targets = []
    for metric in metrics:
        design = metric["design"]
        features.append(
            [
                design["Pc_MPa"],
                design["Tc_K"],
                design["gamma"],
                design["R"],
                design["rt_mm"],
                design["eps"],
                design["spike_deg"],
                design["film_frac"],
                design["cool_frac"],
                design["ch_d_mm"],
                design["ch_n"],
            ]
        )
        targets.append(
            [
                metric["Isp_s"],
                metric["F_N"],
                metric["q_bartz_W_m2"],
                metric["dp_regen_Pa"],
                float(metric["ok"]),
            ]
        )

    names = [
        "Pc_MPa",
        "Tc_K",
        "gamma",
        "R",
        "rt_mm",
        "eps",
        "spike_deg",
        "film_frac",
        "cool_frac",
        "ch_d_mm",
        "ch_n",
    ]
    target_names = ["Isp_s", "F_N", "q_bartz_W_m2", "dp_regen_Pa", "ok"]
    return np.asarray(features, dtype=float), np.asarray(targets, dtype=float), names, target_names


def _pencil_dataset(samples: int, seed: int) -> Tuple[np.ndarray, np.ndarray, list[str], list[str]]:
    from pencil.evaluator import evaluate_batch
    from pencil.sampling import sample_lhs

    designs = sample_lhs(samples, seed=seed, M0_fixed=None, alt_fixed=None)
    metrics = evaluate_batch(designs)

    features = []
    targets = []
    for metric in metrics:
        design = metric["design"]
        features.append(
            [
                design["M0"],
                design["alt_m"],
                design["BPR"],
                design["PRc"],
                design["PRf"],
                design["eta_c"],
                design["eta_f"],
                design["eta_t"],
                design["eta_m"],
                design["pi_d"],
                design["pi_b"],
                design["Tt4"],
                design["m_core"],
            ]
        )
        targets.append(
            [
                metric["spec_thrust_N_per_kgps"],
                metric["TSFC_kg_per_Ns"],
                metric.get("Isp_s", 0.0),
                float(metric["ok"]),
            ]
        )

    names = [
        "M0",
        "alt_m",
        "BPR",
        "PRc",
        "PRf",
        "eta_c",
        "eta_f",
        "eta_t",
        "eta_m",
        "pi_d",
        "pi_b",
        "Tt4",
        "m_core",
    ]
    target_names = ["spec_thrust", "TSFC", "Isp", "ok"]
    return np.asarray(features, dtype=float), np.asarray(targets, dtype=float), names, target_names


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["rocket", "pencil"], required=True)
    parser.add_argument("--samples", type=int, default=1024)
    parser.add_argument("--seed", type=int, default=123)
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    if args.mode == "rocket":
        X, Y, xnames, ynames = _rocket_dataset(args.samples, args.seed)
    else:
        X, Y, xnames, ynames = _pencil_dataset(args.samples, args.seed)

    Path("data/datasets").mkdir(parents=True, exist_ok=True)
    out_path = args.out or f"data/datasets/{args.mode}_{args.samples}.npz"

    np.savez(
        out_path,
        X=X,
        Y=Y,
        xnames=np.asarray(xnames, dtype=object),
        ynames=np.asarray(ynames, dtype=object),
    )
    summary = {"X": list(X.shape), "Y": list(Y.shape), "xnames": xnames, "ynames": ynames}
    Path(out_path.replace(".npz", ".json")).write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({"saved": out_path, "X": list(X.shape), "Y": list(Y.shape)}, ensure_ascii=False, indent=2))

