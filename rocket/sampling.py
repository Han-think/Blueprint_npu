import random
codex/initialize-npu-inference-template-ys4nnv
from typing import Dict, List

from typing import Dict, List, Tuple
main

BOUNDS = {
    "Pc_MPa":     (3.0, 15.0),
    "Tc_K":       (2600.0, 3700.0),
    "gamma":      (1.15, 1.30),
    "R":          (300.0, 380.0),
    "rt_mm":      (10.0, 35.0),
    "eps":        (6.0, 35.0),
    "spike_deg":  (6.0, 22.0),
    "film_frac":  (0.00, 0.15),
    "cool_frac":  (0.06, 0.22),
    "ch_d_mm":    (1.2, 3.0),
    "ch_n":       (60, 180)
}

def _lhs_unit(n: int, d: int, rng: random.Random):
    bins = [list((i + rng.random()) / n for i in range(n)) for _ in range(d)]
    for arr in bins:
        rng.shuffle(arr)
    return [[bins[j][i] for j in range(d)] for i in range(n)]

def _scale(u: float, lo: float, hi: float, is_int: bool = False):
    v = lo + (hi - lo) * u
    return int(round(v)) if is_int else v

def sample_lhs(n: int, seed=None) -> List[Dict]:
    rng = random.Random(seed)
    keys = list(BOUNDS.keys())
    unit = _lhs_unit(n, len(keys), rng)
    out = []
    for row in unit:
        design = {}
        for k, u in zip(keys, row):
            lo, hi = BOUNDS[k]
            is_int = isinstance(lo, int) and isinstance(hi, int)
            design[k] = _scale(u, lo, hi, is_int=is_int)
        out.append(design)
    return out
