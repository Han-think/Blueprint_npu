from __future__ import annotations

import os
from typing import Any, Optional

from .config import load_config
from .evaluator import Evaluator
from .generator import Generator
from .optimizer import Optimizer
from .surrogate import Surrogate


class Pipeline:
    def __init__(self, fake: bool = False, device: Optional[str] = None) -> None:
        cfg = load_config()
        self.gen = Generator(cfg["design_space"])
        self.surr = Surrogate(fake=fake, device=device)
        self.eval = Evaluator(cfg["constraints"])
        self.opt = Optimizer()
        self.fake = fake
        self.device_selected = self.surr.device_selected

    def generate(self, count: int) -> list[list[float]]:
        return self.gen.sample(count)

    def predict(self, designs: list[Any]) -> list[float]:
        ds = [list(map(float, design)) for design in designs]
        return self.surr.predict(ds)

    def evaluate(self, designs: list[Any]) -> list[dict[str, Any]]:
        ds = [list(map(float, design)) for design in designs]
        return self.eval.evaluate(ds)

    def optimize(self, samples: Optional[int] = None, topk: Optional[int] = None) -> list[dict[str, Any]]:
        n = samples or int(os.getenv("BLUEPRINT_SAMPLES", "256"))
        k = topk or int(os.getenv("BLUEPRINT_TOPK", "16"))
        designs = self.generate(n)
        scores = self.predict(designs)
        selected = self.opt.select_topk(designs, scores, k)
        metrics = self.evaluate([design for design, _ in selected])
        return [
            {"design": list(design), "score": score, "metrics": metric}
            for (design, score), metric in zip(selected, metrics)
        ]
