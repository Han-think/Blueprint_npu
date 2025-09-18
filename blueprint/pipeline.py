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
        space = cfg.get("design_space", [])
        constraints = cfg.get("constraints", {})
        self.gen = Generator(space)
        self.surr = Surrogate(fake=fake, device=device)
        self.eval = Evaluator(constraints)
        self.opt = Optimizer()
        self.fake = fake
        self.device_selected = self.surr.device_selected

    def generate(self, n: int) -> List[List[float]]:
        return self.gen.sample(n)

    def predict(self, designs: List[Any]) -> List[float]:
        ds = [list(map(float, d)) for d in designs]
        return self.surr.predict(ds)

    def evaluate(self, designs: List[Any]) -> List[Dict[str, Any]]:
        ds = [list(map(float, d)) for d in designs]
        return self.eval.evaluate(ds)

    def optimize(
        self, samples: Optional[int] = None, topk: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        n = samples or int(os.getenv("BLUEPRINT_SAMPLES", "256"))
        k = topk or int(os.getenv("BLUEPRINT_TOPK", "16"))
        x = self.generate(n)
        y = self.predict(x)
        picked = self.opt.select_topk(x, y, k)
        metrics = self.evaluate([design for design, _ in picked])
        return [
            {"design": design, "score": score, "metrics": metric}
            for (design, score), metric in zip(picked, metrics, strict=True)
        ]
