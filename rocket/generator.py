"""Design sampler for the rocket pipeline."""

from __future__ import annotations

import random

from typing import Dict, List


BOUNDS = {
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


def sample(n: int, seed: int | None = None) -> List[Dict[str, float]]:
    """Sample random rocket design candidates within the configured bounds."""

    rng = random.Random(seed)
    out: List[Dict[str, float]] = []
    for _ in range(n):
        design: Dict[str, float] = {}
        for key, bounds in BOUNDS.items():
            lo, hi = bounds
            if isinstance(lo, float):
                design[key] = rng.uniform(float(lo), float(hi))
            else:
                design[key] = rng.randint(int(lo), int(hi))
        out.append(design)
    return out

