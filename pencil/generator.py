"""Design sampler for the pencil turbofan proxy."""

from __future__ import annotations

import random

from typing import Dict, List, Optional, Tuple

BOUNDS: Dict[str, Tuple[float, float]] = {
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


def sample(
    n: int,
    seed: Optional[int] = None,
    M0_fixed: Optional[float] = None,
    alt_fixed: Optional[float] = None,
) -> List[Dict[str, float]]:
    """Sample turbofan design vectors within predefined bounds."""

    rng = random.Random(seed)
    out: List[Dict[str, float]] = []
    for _ in range(n):
        design: Dict[str, float] = {}
        for key, (lo, hi) in BOUNDS.items():
            if key == "M0" and M0_fixed is not None:
                design[key] = float(M0_fixed)
            elif key == "alt_m" and alt_fixed is not None:
                design[key] = float(alt_fixed)
            else:
                design[key] = rng.uniform(lo, hi)
        out.append(design)
    return out
