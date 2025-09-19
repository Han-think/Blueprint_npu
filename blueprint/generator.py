from __future__ import annotations

from typing import Dict, List

import numpy as np


class Generator:
    def __init__(self, space: List[Dict[str, float]]) -> None:
        self.space = space

    def sample(self, n: int) -> list[list[float]]:
        lows = np.array([item["low"] for item in self.space], dtype=float)
        highs = np.array([item["high"] for item in self.space], dtype=float)
        u = np.random.rand(n, len(self.space))
        samples = lows + (highs - lows) * u
        return samples.tolist()
