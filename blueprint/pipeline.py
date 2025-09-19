from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from .config import load_config
from .evaluator import Evaluator
from .generator import Generator
from .optimizer import Optimizer
from .surrogate import Surrogate


class Pipeline:
    def __init__(self, fake: bool = False, device: Optional[str] = None):
        cfg = load_config()
        self.generator = Generator(cfg["design_space"])
        self.surrogate = Surrogate(fake=fake, device=device)
        self.evaluator = Evaluator(cfg["constraints"])
        self.optimizer = Optimizer()
        self.fake = fake
        self.device_selected = self.surrogate.device_selected

    def generate(self, n: int) -> List[List[float]]:
        return self.generator.sample(n)

    def predict(self, designs: List[Any]) -> List[float]:
        parsed = [list(map(float, d)) for d in designs]
        return self.surrogate.predict(parsed)

    def evaluate(self, designs: List[Any]) -> List[Dict[str, Any]]:
        parsed = [list(map(float, d)) for d in designs]
        return self.evaluator.evaluate(parsed)

    def optimize(self, samples: Optional[int] = None, topk: Optional[int] = None):
        n = samples or int(os.getenv("BLUEPRINT_SAMPLES", "256"))
        k = topk or int(os.getenv("BLUEPRINT_TOPK", "16"))
        designs = self.generate(n)
        scores = self.predict(designs)
        chosen = self.optimizer.select_topk(designs, scores, k)
        metrics = self.evaluate([d for d, _ in chosen])
        return [
            {"design": design, "score": score, "metrics": metric}
            for (design, score), metric in zip(chosen, metrics)
        ]
