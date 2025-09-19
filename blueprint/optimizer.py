from __future__ import annotations

from typing import List, Sequence, Tuple

import numpy as np


class Optimizer:
    def select_topk(
        self, designs: Sequence[Sequence[float]], scores: Sequence[float], k: int
    ) -> List[Tuple[List[float], float]]:
        if k <= 0:
            return []
        idx = np.argsort(np.asarray(scores, dtype=float))[::-1][:k]
        return [([float(v) for v in designs[i]], float(scores[i])) for i in idx]
