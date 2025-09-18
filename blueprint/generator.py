import numpy as np
from typing import List, Dict

class Generator:
    def __init__(self, space: List[Dict[str, float]]):
        self.space = space

    def sample(self, n: int) -> list[list[float]]:
        lows  = np.array([p["low"]  for p in self.space], dtype=float)
        highs = np.array([p["high"] for p in self.space], dtype=float)
        U = np.random.rand(n, len(self.space))
        X = lows + (highs - lows) * U
        return X.tolist()
