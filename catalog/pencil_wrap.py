"""Pencil archetype wrappers for catalog optimization calls."""

from __future__ import annotations

import random

from copy import deepcopy
from typing import Dict, List, Optional, Tuple

from pencil.evaluator import evaluate_batch


BASE_BOUNDS: Dict[str, Tuple[float, float]] = {
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
    "Tt4": (1_600.0, 2_050.0),
    "m_core": (12.0, 35.0),
}


PENCIL_TYPES: Dict[str, Dict] = {
    "turbojet": {
        "overrides": {"BPR": (0.0, 0.2), "PRf": (1.00, 1.15), "PRc": (8.0, 20.0)},
        "post": {"afterburner_gain": 0.0},
    },
    "low_bypass_turbofan": {
        "overrides": {"BPR": (0.2, 1.2), "PRf": (1.2, 1.9), "PRc": (12.0, 36.0)},
        "post": {"afterburner_gain": 0.0},
    },
    "afterburning_turbofan": {
        "overrides": {"BPR": (0.2, 1.0), "PRc": (16.0, 40.0), "Tt4": (1_700.0, 2_100.0)},
        "post": {"afterburner_gain": 0.30, "ab_tsfc_penalty": 0.60},
    },
    "ramjet": {
        "overrides": {
            "PRc": (1.0, 1.1),
            "PRf": (1.0, 1.1),
            "BPR": (0.0, 0.2),
            "Tt4": (1_700.0, 2_200.0),
        },
        "force_M0": (1.2, 3.0),
        "post": {"afterburner_gain": 0.0},
    },
}


def _merge_bounds(base: Dict[str, Tuple[float, float]], cfg: Dict) -> Dict[str, Tuple[float, float]]:
    bounds = deepcopy(base)
    for key, val in cfg.get("overrides", {}).items():
        bounds[key] = val
    if "force_M0" in cfg:
        bounds["M0"] = cfg["force_M0"]
    return bounds


def _sample(
    bounds: Dict[str, Tuple[float, float]],
    n: int,
    seed: int | None,
    M0_fixed: Optional[float],
    alt_fixed: Optional[float],
) -> List[Dict[str, float]]:
    rng = random.Random(seed)
    samples: List[Dict[str, float]] = []
    for _ in range(n):
        design: Dict[str, float] = {}
        for key, (lo, hi) in bounds.items():
            if key == "M0" and M0_fixed is not None:
                design[key] = float(M0_fixed)
            elif key == "alt_m" and alt_fixed is not None:
                design[key] = float(alt_fixed)
            else:
                design[key] = rng.uniform(lo, hi)
        samples.append(design)
    return samples


def _apply_afterburner(metric: Dict[str, float], gain: float, tsfc_penalty: float) -> Dict[str, float]:
    if gain <= 0.0:
        return metric
    adjusted = dict(metric)
    adjusted["F_N"] *= 1.0 + gain
    adjusted["spec_thrust_N_per_kgps"] *= 1.0 + gain
    adjusted["TSFC_kg_per_Ns"] *= 1.0 + tsfc_penalty
    adjusted["score"] = adjusted["spec_thrust_N_per_kgps"] - 2000.0 * adjusted["TSFC_kg_per_Ns"]
    return adjusted


def pencil_optimize(
    kind: str,
    *,
    samples: int = 256,
    topk: int = 16,
    seed: int | None = 123,
    M0: float | None = None,
    alt_m: float | None = None,
) -> List[Dict]:
    """Sample designs for the requested pencil archetype and return top metrics."""

    if kind not in PENCIL_TYPES:
        raise ValueError(f"unknown pencil type: {kind}")
    cfg = PENCIL_TYPES[kind]
    bounds = _merge_bounds(BASE_BOUNDS, cfg)
    designs = _sample(bounds, samples, seed, M0, alt_m)
    metrics = evaluate_batch(designs)
    gain = cfg.get("post", {}).get("afterburner_gain", 0.0)
    penalty = cfg.get("post", {}).get("ab_tsfc_penalty", 0.0)
    metrics = [_apply_afterburner(m, gain, penalty) for m in metrics]
    metrics.sort(key=lambda m: (m["ok"], m["score"]), reverse=True)
    return metrics[:topk]

