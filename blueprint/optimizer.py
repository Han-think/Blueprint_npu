from __future__ import annotations

from typing import List, Sequence, Tuple

import numpy as np


class Optimizer:
    def select_topk(
        self, designs: Sequence[Sequence[float]], scores: Sequence[float], k: int
    ) -> List[Tuple[List[float], float]]:
        if k <= 0:
            return []
        arr_scores = np.asarray(scores, dtype=float)
        idx = np.argsort(arr_scores)[::-1][:k]
        return [
            (list(map(float, designs[i])), float(arr_scores[i]))
            for i in idx.tolist()
        ]
