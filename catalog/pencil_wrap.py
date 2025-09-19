from __future__ import annotations

import random
from copy import deepcopy
from typing import Dict, Optional

from pencil.evaluator import evaluate_batch

BASE_BOUNDS = {
    "M0": (0.0, 2.0),
    "alt_m": (0.0, 12_000.0),
    "BPR": (0.1, 1.2),
    "PRc": (12.0, 36.0),
    "PRf": (1.2, 1.9),
    "eta_c": (0.85, 0.90),
    "eta_f": (0.85, 0.90),
    "eta_t": (0.88, 0.92),
    "eta_m": (0.96, 0.995),
    "pi_d": (0.90, 0.99),
    "pi_b": (0.93, 0.98),
    "Tt4": (1600.0, 2050.0),
    "m_core": (12.0, 35.0),
}

PENCIL_TYPES: Dict[str, Dict] = {
    "turbojet": {
        "overrides": {"BPR": (0.0, 0.2), "PRf": (1.0, 1.15), "PRc": (8.0, 20.0)},
        "post": {"afterburner_gain": 0.0},
    },
    "low_bypass_turbofan": {
        "overrides": {"BPR": (0.2, 1.2), "PRf": (1.2, 1.9), "PRc": (12.0, 36.0)},
        "post": {"afterburner_gain": 0.0},
    },
    "afterburning_turbofan": {
        "overrides": {"BPR": (0.2, 1.0), "PRc": (16.0, 40.0), "Tt4": (1700.0, 2100.0)},
        "post": {"afterburner_gain": 0.30, "ab_tsfc_penalty": 0.60},
    },
    "ramjet": {
        "overrides": {"PRc": (1.0, 1.1), "PRf": (1.0, 1.1), "BPR": (0.0, 0.2), "Tt4": (1700.0, 2200.0)},
        "force_M0": (1.2, 3.0),
        "post": {"afterburner_gain": 0.0},
    },
}


def _merge_bounds(base: Dict[str, tuple], cfg: Dict) -> Dict[str, tuple]:
    merged = deepcopy(base)
    for key, value in cfg.get("overrides", {}).items():
        merged[key] = value
    if "force_M0" in cfg:
        merged["M0"] = cfg["force_M0"]
    return merged


def _sample(bounds: Dict[str, tuple], n: int, seed: int | None, M0_fixed: Optional[float], alt_fixed: Optional[float]):
    rng = random.Random(seed)
    samples = []
    for _ in range(n):
        design = {}
        for key, (lo, hi) in bounds.items():
            if key == "M0" and M0_fixed is not None:
                design[key] = float(M0_fixed)
            elif key == "alt_m" and alt_fixed is not None:
                design[key] = float(alt_fixed)
            else:
                design[key] = rng.uniform(lo, hi)
        samples.append(design)
    return samples


def _apply_afterburner(metric: Dict, gain: float, tsfc_penalty: float):
    if gain <= 0.0:
        return metric
    modified = dict(metric)
    modified["F_N"] *= 1.0 + gain
    modified["spec_thrust_N_per_kgps"] *= 1.0 + gain
    modified["TSFC_kg_per_Ns"] *= 1.0 + tsfc_penalty
    modified["score"] = modified["spec_thrust_N_per_kgps"] - 2000.0 * modified["TSFC_kg_per_Ns"]
    return modified


def pencil_optimize(kind: str, samples: int = 256, topk: int = 16, seed: int | None = 123, M0: float | None = None, alt_m: float | None = None):
    if kind not in PENCIL_TYPES:
        raise ValueError(f"unknown pencil type: {kind}")
    cfg = PENCIL_TYPES[kind]
    bounds = _merge_bounds(BASE_BOUNDS, cfg)
    designs = _sample(bounds, samples, seed, M0, alt_m)
    metrics = evaluate_batch(designs)
    gain = cfg.get("post", {}).get("afterburner_gain", 0.0)
    penalty = cfg.get("post", {}).get("ab_tsfc_penalty", 0.0)
    metrics = [_apply_afterburner(metric, gain, penalty) for metric in metrics]
    metrics.sort(key=lambda metric: (metric["ok"], metric["score"]), reverse=True)
    return metrics[:topk]
