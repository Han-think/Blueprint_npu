from __future__ import annotations

import random
from typing import Callable, Dict, List, Sequence

from moo.pareto import pareto_front


def nsga_lite(
    population: List[Dict],
    objective: Callable[[Dict], Sequence[float]],
    minimize: Sequence[bool],
    rng: random.Random,
    generations: int = 10,
    crossover_prob: float = 0.9,
    mutation_prob: float = 0.2,
):
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
        y = dict(x)
        for key, value in x.items():
            if rng.random() < mutation_prob and isinstance(value, (int, float)):
                y[key] = value * (0.9 + 0.2 * rng.random())
        return y

    def evaluate(pop):
        values = [objective(p) for p in pop]
        indices = pareto_front(values, minimize)
        return indices, values

    for _ in range(generations):
        front_indices, _ = evaluate(population)
        front = [population[i] for i in front_indices]
        children = []
        while len(children) < max(2, len(population) // 2):
            parents = rng.sample(front if len(front) >= 2 else population, 2)
            if rng.random() < crossover_prob:
                child = crossover(parents[0], parents[1])
            else:
                child = dict(rng.choice(parents))
            child = mutate(child)
            children.append(child)
        population = population + children
        _, values = evaluate(population)
        pareto_indices = pareto_front(values, minimize)
        pareto_pop = [population[i] for i in pareto_indices]
        if len(pareto_pop) < len(population) // 2:
            population = pareto_pop + rng.sample(population, k=len(population) // 2 - len(pareto_pop))
        else:
            population = pareto_pop[: len(population) // 2]
    final_indices, _ = evaluate(population)
    return [population[i] for i in final_indices]
