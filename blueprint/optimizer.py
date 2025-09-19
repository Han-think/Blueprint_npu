from __future__ import annotations

from typing import Sequence, Tuple

import numpy as np


class Optimizer:
    def select_topk(
        self, designs: Sequence[Sequence[float]], scores: Sequence[float], k: int
    ) -> list[Tuple[Sequence[float], float]]:
        order = np.argsort(np.asarray(scores))[::-1][:k]
        return [(designs[idx], float(scores[idx])) for idx in order]
