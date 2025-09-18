from __future__ import annotations

from typing import Any, Dict, List

import numpy as np


class Evaluator:
    def __init__(self, constraints: Dict[str, float]):
        self.constraints = constraints

    def evaluate(self, designs: List[List[float]]) -> List[Dict[str, Any]]:
        x = np.asarray(designs, dtype=float)
        if x.ndim != 2:
            x = np.atleast_2d(x)
        max_abs = np.max(np.abs(x), axis=1)
        sum_abs = np.sum(np.abs(x), axis=1)
        limit_max = float(self.constraints.get("max_abs", float("inf")))
        limit_sum = float(self.constraints.get("sum_limit", float("inf")))
        ok1 = max_abs <= limit_max
        ok2 = sum_abs <= limit_sum
        return [
            {
                "ok": bool(o1 and o2),
                "max_abs": float(a),
                "sum_abs": float(s),
            }
            for o1, o2, a, s in zip(ok1, ok2, max_abs, sum_abs, strict=True)
        ]
