from __future__ import annotations

from typing import List, Optional

from pencil.evaluator import evaluate_batch
from pencil.generator import sample as sample_random
from pencil.sampling import sample_lhs


class PencilPipeline:
    def optimize(
        self,
        samples: int = 256,
        topk: int = 16,
        seed: Optional[int] = None,
        M0: Optional[float] = None,
        alt_m: Optional[float] = None,
        method: str = "lhs",
    ) -> List[dict]:
        if method == "lhs":
            designs = sample_lhs(samples, seed=seed, M0_fixed=M0, alt_fixed=alt_m)
        else:
            designs = sample_random(samples, seed=seed, M0_fixed=M0, alt_fixed=alt_m)
        metrics = evaluate_batch(designs)
        metrics.sort(key=lambda item: (item["ok"], item["score"]), reverse=True)
        return metrics[:topk]
