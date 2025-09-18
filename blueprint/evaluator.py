import numpy as np
from typing import Dict, Any

class Evaluator:
    def __init__(self, constraints: Dict[str, float]):
        self.c = constraints

    def evaluate(self, designs: list[list[float]]) -> list[Dict[str, Any]]:
        X = np.asarray(designs, dtype=float)
        max_abs = np.max(np.abs(X), axis=1)
        sum_abs = np.sum(np.abs(X), axis=1)
        ok1 = max_abs <= self.c.get("max_abs", 1e9)
        ok2 = sum_abs <= self.c.get("sum_limit", 1e9)
        return [
            {"ok": bool(o1 and o2), "max_abs": float(a), "sum_abs": float(s)}
            for o1, o2, a, s in zip(ok1, ok2, max_abs, sum_abs)
        ]
