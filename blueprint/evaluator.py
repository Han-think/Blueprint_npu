from __future__ import annotations

from typing import Any, Dict, List

import numpy as np


class Evaluator:
    def __init__(self, constraints: Dict[str, float]) -> None:
        self.constraints = constraints

    def evaluate(self, designs: List[List[float]]) -> list[Dict[str, Any]]:
        array = np.asarray(designs, dtype=float)
        max_abs = np.max(np.abs(array), axis=1)
        sum_abs = np.sum(np.abs(array), axis=1)
        ok1 = max_abs <= self.constraints.get("max_abs", float("inf"))
        ok2 = sum_abs <= self.constraints.get("sum_limit", float("inf"))
        return [
            {"ok": bool(o1 and o2), "max_abs": float(a), "sum_abs": float(s)}
            for o1, o2, a, s in zip(ok1, ok2, max_abs, sum_abs)
        ]
