from __future__ import annotations

from typing import List, Optional

from rocket.evaluator import evaluate_batch
from rocket.generator import sample as sample_random
from rocket.sampling import sample_lhs


class RocketPipeline:
    def optimize(
        self,
        samples: int = 256,
        topk: int = 16,
        pa_kpa: float = 101.325,
        seed: Optional[int] = None,
        method: str = "lhs",
    ) -> List[dict]:
        if method == "lhs":
            designs = sample_lhs(samples, seed=seed)
        else:
            designs = sample_random(samples, seed=seed)
        metrics = evaluate_batch(designs, pa_kpa=pa_kpa)
        metrics.sort(key=lambda item: (item["ok"], item["score"]), reverse=True)
        return metrics[:topk]
