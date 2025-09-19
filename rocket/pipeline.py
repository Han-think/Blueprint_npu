"""Pipeline wiring for the rocket optimization flow."""

from __future__ import annotations

from typing import Dict, List, Optional

from .evaluator import evaluate_batch
from .generator import sample


class RocketPipeline:
    """Provide a simple optimize interface returning the best candidates."""

    def optimize(
        self,
        samples: Optional[int] = 256,
        topk: Optional[int] = 16,
        pa_kpa: Optional[float] = 101.325,
        seed: Optional[int] = None,
    ) -> List[Dict[str, float]]:
        total = samples or 256
        keep = topk or 16
        designs = sample(total, seed=seed)
        metrics = evaluate_batch(designs, pa_kpa=pa_kpa or 101.325)
        metrics.sort(key=lambda item: item["score"], reverse=True)
        return metrics[:keep]

