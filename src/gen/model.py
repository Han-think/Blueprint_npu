from __future__ import annotations

import os
import random
from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass
class DesignBounds:
    Pc: Tuple[float, float] = (5.0e6, 8.0e6)  # Pa
    throat_D: Tuple[float, float] = (0.03, 0.06)  # m
    area_ratio: Tuple[float, float] = (5.0, 20.0)  # Ae/At


def _rand(a: float, b: float, rng: random.Random) -> float:
    return a + (b - a) * rng.random()


def sample_designs(bounds: DesignBounds, n: int = 8, seed: int = 0) -> List[Dict[str, float]]:
    """Parameter sampler placeholder until OV generator is integrated."""
    _ = os.environ.get("OV_GEN_XML")  # placeholder for future integration
    rng = random.Random(seed)
    designs: List[Dict[str, float]] = []
    for _idx in range(n):
        pc = _rand(*bounds.Pc, rng)
        throat_d = _rand(*bounds.throat_D, rng)
        area_ratio = _rand(*bounds.area_ratio, rng)
        designs.append({"Pc": pc, "throat_D": throat_d, "area_ratio": area_ratio})
    return designs
