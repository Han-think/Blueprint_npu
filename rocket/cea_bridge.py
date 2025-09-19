from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Tuple

import numpy as np


def load_table(path: str = "data/cea_table.csv") -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    table = Path(path)
    if not table.is_file():
        raise FileNotFoundError(f"CEA table not found: {path}")
    Pc, eps, isp = [], [], []
    with table.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            Pc.append(float(row["Pc_MPa"]))
            eps.append(float(row["eps"]))
            isp.append(float(row["Isp_s"]))
    return np.asarray(Pc), np.asarray(eps), np.asarray(isp)


def nearest_Isp(Pc_MPa: float, eps_v: float, Pc_tab: np.ndarray, eps_tab: np.ndarray, Isp_tab: np.ndarray) -> float:
    dv = np.abs(Pc_tab - Pc_MPa) + 0.5 * np.abs(eps_tab - eps_v)
    idx = int(np.argmin(dv))
    return float(Isp_tab[idx])


def fit_isp_scale(n_samples: int = 400, seed: int = 42, table_path: str = "data/cea_table.csv") -> float:
    from rocket.sampling import sample_lhs as sample
    from rocket.evaluator import evaluate_batch

    Pc_tab, eps_tab, isp_tab = load_table(table_path)
    designs = sample(n_samples, seed=seed)
    metrics = evaluate_batch(designs)
    ratios = []
    for metric in metrics:
        design = metric["design"]
        isp_pred = float(metric["Isp_s"])
        isp_ref = nearest_Isp(design["Pc_MPa"], design["eps"], Pc_tab, eps_tab, isp_tab)
        if isp_pred > 1e-6:
            ratios.append(isp_ref / isp_pred)
    if not ratios:
        return 1.0
    return float(np.median(np.asarray(ratios, dtype=float)))


def update_calib_json(isp_scale: float, path: str = "data/cea_calib.json"):
    config_path = Path(path)
    if config_path.is_file():
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
        except Exception:  # pragma: no cover - defensive
            data = {}
    else:
        data = {}
    data["isp_scale"] = float(isp_scale)
    config_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data
