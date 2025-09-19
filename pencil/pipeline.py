"""Optimization pipeline for the pencil turbofan proxy."""

from __future__ import annotations

from typing import Dict, List, Optional

from .evaluator import evaluate_batch
from .generator import sample


class PencilPipeline:
    """Generate, evaluate, and rank pencil turbofan designs."""

    def optimize(
        self,
        samples: int = 256,
        topk: int = 16,
        seed: Optional[int] = None,
        M0: Optional[float] = None,
        alt_m: Optional[float] = None,
    ) -> List[Dict[str, float]]:
        """Return the top designs sorted by feasibility and score."""

        designs = sample(samples, seed=seed, M0_fixed=M0, alt_fixed=alt_m)
        metrics = evaluate_batch(designs)
        metrics.sort(key=lambda item: (item["ok"], item["score"]), reverse=True)
        return metrics[:topk]
