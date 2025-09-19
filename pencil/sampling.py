import random
from typing import Dict, List

BOUNDS = {
    "M0":       (0.0, 2.0),
    "alt_m":    (0.0, 12000.0),
    "BPR":      (0.1, 1.2),
    "PRc":      (12.0, 36.0),
    "PRf":      (1.2, 1.9),
    "eta_c":    (0.85, 0.90),
    "eta_f":    (0.85, 0.90),
    "eta_t":    (0.88, 0.92),
    "eta_m":    (0.96, 0.995),
    "pi_d":     (0.90, 0.99),
    "pi_b":     (0.93, 0.98),
    "Tt4":      (1600.0, 2050.0),
    "m_core":   (12.0, 35.0),
}

def _lhs_unit(n: int, d: int, rng: random.Random):
    bins = [list((i + rng.random()) / n for i in range(n)) for _ in range(d)]
    for arr in bins:
        rng.shuffle(arr)
    return [[bins[j][i] for j in range(d)] for i in range(n)]

def _scale(u: float, lo: float, hi: float):
    return lo + (hi - lo) * u

def sample_lhs(n: int, seed=None, M0_fixed=None, alt_fixed=None) -> List[Dict]:
    rng = random.Random(seed)
    keys = list(BOUNDS.keys())
    unit = _lhs_unit(n, len(keys), rng)
    out = []
    for row in unit:
        design = {}
        for k, u in zip(keys, row):
            lo, hi = BOUNDS[k]
            design[k] = _scale(u, lo, hi)
        if M0_fixed is not None:
            design["M0"] = float(M0_fixed)
        if alt_fixed is not None:
            design["alt_m"] = float(alt_fixed)
        out.append(design)
    return out
