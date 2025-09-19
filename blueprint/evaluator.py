from __future__ import annotations

from typing import Any, Dict, List

import numpy as np


class Evaluator:
    def __init__(self, constraints: Dict[str, float]):
        self.constraints = constraints

    def evaluate(self, designs: List[List[float]]) -> List[Dict[str, Any]]:
        x = np.asarray(designs, dtype=float)
        max_abs = np.max(np.abs(x), axis=1)
        sum_abs = np.sum(np.abs(x), axis=1)
        max_limit = self.constraints.get("max_abs", float("inf"))
        sum_limit = self.constraints.get("sum_limit", float("inf"))
        results = []
        for a, s in zip(max_abs, sum_abs):
            ok = bool(a <= max_limit and s <= sum_limit)
            results.append({"ok": ok, "max_abs": float(a), "sum_abs": float(s)})
        return results
