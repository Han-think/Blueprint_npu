import os
from typing import Optional, Any
from .config import load_config
from .generator import Generator
from .surrogate import Surrogate
from .evaluator import Evaluator
from .optimizer import Optimizer

class Pipeline:
    def __init__(self, fake: bool = False, device: Optional[str] = None):
        cfg = load_config()
        self.gen = Generator(cfg["design_space"])
        self.surr = Surrogate(fake=fake, device=device)
        self.eval = Evaluator(cfg["constraints"])
        self.opt = Optimizer()
        self.fake = fake
        self.device_selected = self.surr.device_selected

    def generate(self, n: int):
        return self.gen.sample(n)

    def predict(self, designs: list[Any]):
        ds = [list(map(float, d)) for d in designs]
        return self.surr.predict(ds)

    def evaluate(self, designs: list[Any]):
        ds = [list(map(float, d)) for d in designs]
        return self.eval.evaluate(ds)

    def optimize(self, samples: Optional[int] = None, topk: Optional[int] = None):
        n = samples or int(os.getenv("BLUEPRINT_SAMPLES", "256"))
        k = topk or int(os.getenv("BLUEPRINT_TOPK", "16"))
        X = self.generate(n)
        y = self.predict(X)
        picked = self.opt.select_topk(X, y, k)
        metrics = self.evaluate([d for d, _ in picked])
        return [{"design": d, "score": s, "metrics": m} for (d, s), m in zip(picked, metrics)]
