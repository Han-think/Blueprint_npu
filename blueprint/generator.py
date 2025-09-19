 codex/initialize-npu-inference-template-v1n7c2
from __future__ import annotations

from typing import Dict, List

import numpy as np


import numpy as np
from typing import List, Dict
 main

class Generator:
    def __init__(self, space: List[Dict[str, float]]):
        self.space = space

 codex/initialize-npu-inference-template-v1n7c2
    def sample(self, n: int) -> List[List[float]]:
        lows = np.array([float(p["low"]) for p in self.space], dtype=float)
        highs = np.array([float(p["high"]) for p in self.space], dtype=float)
        u = np.random.rand(n, len(self.space))
        x = lows + (highs - lows) * u
        return x.tolist()

    def sample(self, n: int) -> list[list[float]]:
        lows  = np.array([p["low"]  for p in self.space], dtype=float)
        highs = np.array([p["high"] for p in self.space], dtype=float)
        U = np.random.rand(n, len(self.space))
        X = lows + (highs - lows) * U
        return X.tolist()
 main
