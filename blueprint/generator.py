from __future__ import annotations

from typing import Dict, List

import numpy as np


class Generator:
    def __init__(self, space: List[Dict[str, float]]):
        self.space = space

    def sample(self, n: int) -> list[list[float]]:
        lows = np.array([float(p["low"]) for p in self.space], dtype=float)
        highs = np.array([float(p["high"]) for p in self.space], dtype=float)
        u = np.random.rand(n, len(self.space))
        x = lows + (highs - lows) * u
        return x.tolist()
