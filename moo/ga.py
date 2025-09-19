from typing import Callable, Dict, List, Sequence
import random
from moo.pareto import pareto_front

def nsga_lite(pop: List[Dict], obj: Callable[[Dict], Sequence[float]], minimize: Sequence[bool], rng: random.Random, gens: int = 10, pc: float = 0.9, pm: float = 0.2):
    def crossover(a: Dict, b: Dict):
        child = {}
        for key in a.keys():
            va, vb = a[key], b[key]
            if isinstance(va, (int, float)) and isinstance(vb, (int, float)):
                alpha = rng.random()
                child[key] = (1 - alpha) * va + alpha * vb
            else:
                child[key] = rng.choice([va, vb])
        return child

    def mutate(x: Dict):
        mutated = dict(x)
        for key, value in x.items():
            if rng.random() < pm and isinstance(value, (int, float)):
                mutated[key] = value * (0.9 + 0.2 * rng.random())
        return mutated

    def evaluate(population: List[Dict]):
        vals = [obj(p) for p in population]
        idx = pareto_front(vals, minimize)
        return idx, vals

    for _ in range(gens):
        idx, _ = evaluate(pop)
        front = [pop[i] for i in idx]

        children: List[Dict] = []
        while len(children) < max(2, len(pop) // 2):
            parents = front if len(front) >= 2 else pop
            a, b = rng.sample(parents, 2)
            if rng.random() < pc:
                child = crossover(a, b)
            else:
                child = dict(rng.choice([a, b]))
            children.append(mutate(child))

        pop = pop + children
        _, vals = evaluate(pop)
        idx = pareto_front(vals, minimize)
        pareto_pop = [pop[i] for i in idx]

        target = len(pop) // 2
        if len(pareto_pop) >= target:
            pop = pareto_pop[:target]
        else:
            remaining = target - len(pareto_pop)
            others = [item for idx_, item in enumerate(pop) if idx_ not in idx]
            rng.shuffle(others)
            pop = pareto_pop + others[:remaining]

    idx, _ = evaluate(pop)
    return [pop[i] for i in idx]
