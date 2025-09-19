"""Utility helpers to calibrate Isp scaling from a CEA table."""
from __future__ import annotations

from pathlib import Path
from typing import Tuple
import csv
import json

import numpy as np


def load_table(path: str = "data/cea_table.csv") -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Load a CEA lookup table with Pc_MPa, eps, and Isp_s columns."""
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"CEA table not found: {path}")
    pc_vals: list[float] = []
    eps_vals: list[float] = []
    isp_vals: list[float] = []
    with p.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pc_vals.append(float(row["Pc_MPa"]))
            eps_vals.append(float(row["eps"]))
            isp_vals.append(float(row["Isp_s"]))
    return np.asarray(pc_vals), np.asarray(eps_vals), np.asarray(isp_vals)


def nearest_isp(
    pc_mpa: float,
    eps_value: float,
    pc_tab: np.ndarray,
    eps_tab: np.ndarray,
    isp_tab: np.ndarray,
) -> float:
    """Return the nearest reference Isp using an L1 metric in (Pc, eps)."""
    distances = np.abs(pc_tab - pc_mpa) + 0.5 * np.abs(eps_tab - eps_value)
    index = int(np.argmin(distances))
    return float(isp_tab[index])


def fit_isp_scale(
    n_samples: int = 400,
    seed: int = 42,
    table_path: str = "data/cea_table.csv",
) -> float:
    """Estimate a scalar correction factor aligning surrogate Isp to CEA values."""
    from rocket.sampling import sample_lhs
    from rocket.evaluator import evaluate_batch

    pc_tab, eps_tab, isp_tab = load_table(table_path)
    designs = sample_lhs(n_samples, seed=seed)
    metrics = evaluate_batch(designs)

    ratios: list[float] = []
    for metric in metrics:
        design = metric["design"]
        isp_pred = float(metric["Isp_s"])
        isp_ref = nearest_isp(design["Pc_MPa"], design["eps"], pc_tab, eps_tab, isp_tab)
        if isp_pred > 1e-6:
            ratios.append(isp_ref / isp_pred)
    if not ratios:
        return 1.0
    return float(np.median(np.asarray(ratios, dtype=float)))


def update_calib_json(isp_scale: float, path: str = "data/cea_calib.json") -> dict:
    """Update the calibration JSON with a new Isp scale factor."""
    p = Path(path)
    if p.is_file():
        try:
            cfg = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            cfg = {}
    else:
        cfg = {}
    cfg["isp_scale"] = float(isp_scale)
    p.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    return cfg
