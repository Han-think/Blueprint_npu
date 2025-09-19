"""Rocket archetype sampling helpers for the catalog API."""

from __future__ import annotations

import random
from copy import deepcopy
from typing import Dict, List, Tuple

from rocket.evaluator import evaluate_batch


# Base bounds mirror the rocket generator defaults.
BASE_BOUNDS: Dict[str, Tuple[float, float]] = {
    "Pc_MPa": (3.0, 15.0),
    "Tc_K": (2600.0, 3700.0),
    "gamma": (1.15, 1.30),
    "R": (300.0, 380.0),
    "rt_mm": (10.0, 35.0),
    "eps": (6.0, 35.0),
    "spike_deg": (6.0, 22.0),
    "film_frac": (0.00, 0.15),
    "cool_frac": (0.06, 0.22),
    "ch_d_mm": (1.2, 3.0),
    "ch_n": (60, 180),
}


ROCKET_TYPES: Dict[str, Dict[str, Dict[str, Tuple[float, float]]]] = {
    "pressure_fed": {
        "note": "Pressure-fed storable cycle",
        "overrides": {"Pc_MPa": (2.0, 5.0)},
        "bias": {"eps": (6.0, 15.0)},
    },
    "gas_generator_kerolox": {
        "note": "Gas generator kerolox",
        "overrides": {
            "Tc_K": (3000.0, 3600.0),
            "gamma": (1.18, 1.27),
            "R": (320.0, 360.0),
        },
    },
    "staged_combustion_fr_methalox": {
        "note": "Fuel-rich staged combustion (methalox)",
        "overrides": {
            "Pc_MPa": (10.0, 25.0),
            "Tc_K": (3200.0, 3700.0),
            "gamma": (1.18, 1.26),
        },
        "bias": {"eps": (15.0, 40.0)},
    },
    "staged_combustion_or_methalox": {
        "note": "Ox-rich staged combustion (methalox)",
        "overrides": {
            "Pc_MPa": (12.0, 28.0),
            "Tc_K": (3200.0, 3650.0),
            "gamma": (1.17, 1.24),
        },
        "bias": {"film_frac": (0.00, 0.10)},
    },
    "expander_hydrolox": {
        "note": "Expander cycle (hydrolox)",
        "overrides": {
            "Tc_K": (2800.0, 3400.0),
            "gamma": (1.18, 1.26),
            "R": (340.0, 380.0),
        },
        "bias": {"rt_mm": (8.0, 18.0), "eps": (20.0, 60.0)},
    },
    "expander_bleed_hydrolox": {
        "note": "Expander-bleed (hydrolox)",
        "overrides": {"Tc_K": (2800.0, 3350.0)},
        "bias": {"cool_frac": (0.10, 0.22)},
    },
    "electric_pump_methanolox": {
        "note": "Electric pump methanol-LOX",
        "overrides": {"Pc_MPa": (5.0, 12.0)},
        "bias": {"eps": (8.0, 25.0)},
    },
    "hybrid_htpb_lox": {
        "note": "Hybrid HTPB/LOX",
        "overrides": {
            "Tc_K": (2700.0, 3200.0),
            "gamma": (1.16, 1.25),
        },
        "bias": {"film_frac": (0.04, 0.15)},
    },
    "solid_srb": {
        "note": "Solid rocket booster",
        "overrides": {
            "Tc_K": (2600.0, 3200.0),
            "gamma": (1.18, 1.27),
            "R": (300.0, 340.0),
        },
        "bias": {"cool_frac": (0.00, 0.05)},
    },
    "aerospike_methalox": {
        "note": "Aerospike methalox",
        "overrides": {
            "spike_deg": (6.0, 14.0),
            "eps": (15.0, 60.0),
        },
        "bias": {
            "film_frac": (0.00, 0.12),
            "cool_frac": (0.08, 0.22),
        },
    },
}


def _merge_bounds(base: Dict[str, Tuple[float, float]], cfg: Dict) -> Dict[str, Tuple[float, float]]:
    bounds = deepcopy(base)
    for key, val in cfg.get("overrides", {}).items():
        bounds[key] = val
    for key, val in cfg.get("bias", {}).items():
        bounds[key] = val
    return bounds


def _sample(bounds: Dict[str, Tuple[float, float]], n: int, seed: int | None) -> List[Dict[str, float]]:
    rng = random.Random(seed)
    samples: List[Dict[str, float]] = []
    for _ in range(n):
        design: Dict[str, float] = {}
        for key, (lo, hi) in bounds.items():
            if isinstance(lo, float):
                design[key] = rng.uniform(lo, hi)
            else:
                design[key] = rng.randint(int(lo), int(hi))
        samples.append(design)
    return samples


def rocket_optimize(
    kind: str,
    *,
    samples: int = 256,
    topk: int = 16,
    seed: int | None = 123,
    pa_kpa: float = 101.325,
) -> List[Dict]:
    """Sample designs for the requested archetype and return sorted metrics."""

    if kind not in ROCKET_TYPES:
        raise ValueError(f"unknown rocket type: {kind}")
    bounds = _merge_bounds(BASE_BOUNDS, ROCKET_TYPES[kind])
    designs = _sample(bounds, samples, seed)
    metrics = evaluate_batch(designs, pa_kpa=pa_kpa)
    metrics.sort(key=lambda m: (m["ok"], m["Isp_s"], m["score"]), reverse=True)
    return metrics[:topk]

