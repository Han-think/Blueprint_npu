import numpy as np

class Optimizer:
    def select_topk(self, designs: list[list[float]], scores: list[float], k: int):
        idx = np.argsort(np.array(scores))[::-1][:k]
        return [(designs[i], float(scores[i])) for i in idx.tolist()]
