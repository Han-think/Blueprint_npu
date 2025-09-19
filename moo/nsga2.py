from __future__ import annotations

import math
import random
from typing import Callable, Dict, List, Sequence, Tuple


def _dominates(a: Sequence[float], b: Sequence[float], minimize: Sequence[bool]) -> bool:
    better = True
    strictly = False
    for ai, bi, minimise in zip(a, b, minimize):
        if minimise:
            if ai > bi:
                better = False
            if ai < bi:
                strictly = True
        else:
            if ai < bi:
                better = False
            if ai > bi:
                strictly = True
    return better and strictly


def fast_non_dominated_sort(values: List[Sequence[float]], minimize: Sequence[bool]) -> List[List[int]]:
    n = len(values)
    S = [[] for _ in range(n)]
    domination_count = [0] * n
    rank = [None] * n
    fronts = [[]]
    for p in range(n):
        S[p] = []
        domination_count[p] = 0
        for q in range(n):
            if _dominates(values[p], values[q], minimize):
                S[p].append(q)
            elif _dominates(values[q], values[p], minimize):
                domination_count[p] += 1
        if domination_count[p] == 0:
            rank[p] = 0
            fronts[0].append(p)
    i = 0
    while fronts[i]:
        next_front = []
        for p in fronts[i]:
            for q in S[p]:
                domination_count[q] -= 1
                if domination_count[q] == 0:
                    rank[q] = i + 1
                    next_front.append(q)
        i += 1
        fronts.append(next_front)
    if not fronts[-1]:
        fronts.pop()
    return fronts


def crowding_distance(indices: List[int], values: List[Sequence[float]], minimize: Sequence[bool]) -> Dict[int, float]:
    distance = {i: 0.0 for i in indices}
    if len(indices) <= 2:
        for i in indices:
            distance[i] = float("inf")
        return distance
    objectives = len(values[0])
    for m in range(objectives):
        sorted_idx = sorted(indices, key=lambda i: values[i][m])
        if not minimize[m]:
            sorted_idx = list(reversed(sorted_idx))
        fmin = values[sorted_idx[0]][m]
        fmax = values[sorted_idx[-1]][m]
        distance[sorted_idx[0]] = distance[sorted_idx[-1]] = float("inf")
        denom = (fmax - fmin) if abs(fmax - fmin) > 1e-12 else 1.0
        for k in range(1, len(sorted_idx) - 1):
            prev_idx = sorted_idx[k - 1]
            next_idx = sorted_idx[k + 1]
            distance[sorted_idx[k]] += (values[next_idx][m] - values[prev_idx][m]) / denom
    return distance


def tournament(a: int, b: int, ranks: Dict[int, int], cd: Dict[int, float], rng: random.Random) -> int:
    if ranks[a] < ranks[b]:
        return a
    if ranks[b] < ranks[a]:
        return b
    return a if cd[a] >= cd[b] else b


def sbx_crossover(x: Dict, y: Dict, rng: random.Random, eta: float = 10.0, prob: float = 0.9) -> Dict:
    if rng.random() > prob:
        return dict(x if rng.random() < 0.5 else y)
    child = {}
    for key in x.keys():
        vx, vy = x[key], y[key]
        if not isinstance(vx, (int, float)) or not isinstance(vy, (int, float)):
            child[key] = rng.choice([vx, vy])
            continue
        if vx == vy:
            child[key] = vx
            continue
        xl, xu = (min(vx, vy), max(vx, vy))
        u = rng.random()
        beta = (2 * u) ** (1 / (eta + 1)) if u <= 0.5 else (1 / (2 * (1 - u))) ** (1 / (eta + 1))
        value = 0.5 * ((1 + beta) * vx + (1 - beta) * vy)
        lo = xl - 0.25 * (xu - xl)
        hi = xu + 0.25 * (xu - xl)
        child[key] = max(min(value, hi), lo)
    return child


def poly_mutation(x: Dict, rng: random.Random, eta: float = 12.0, prob: float = 0.15) -> Dict:
    mutated = dict(x)
    for key, value in x.items():
        if isinstance(value, (int, float)) and rng.random() < prob:
            u = rng.random()
            delta = (2 * u) ** (1 / (eta + 1)) - 1 if u < 0.5 else 1 - (2 * (1 - u)) ** (1 / (eta + 1))
            mutated[key] = value * (1 + 0.15 * delta)
    return mutated


def nsga2(
    initial: List[Dict],
    objective: Callable[[Dict], Sequence[float]],
    minimize: Sequence[bool],
    rng: random.Random,
    generations: int = 20,
    pop_size: int | None = None,
) -> List[Dict]:
    population = list(initial)
    if pop_size is None:
        pop_size = len(population)

    def evaluate(pop: List[Dict]) -> Tuple[List[List[int]], List[Sequence[float]], Dict[int, int], Dict[int, float]]:
        vals = [objective(p) for p in pop]
        fronts = fast_non_dominated_sort(vals, minimize)
        ranks = {}
        for rank_value, front in enumerate(fronts):
            for idx in front:
                ranks[idx] = rank_value
        cd: Dict[int, float] = {}
        for front in fronts:
            cd.update(crowding_distance(front, vals, minimize))
        return fronts, vals, ranks, cd

    for _ in range(generations):
        fronts, vals, ranks, cd = evaluate(population)
        mating_pool = []
        while len(mating_pool) < len(population):
            i = rng.randrange(len(population))
            j = rng.randrange(len(population))
            winner = tournament(i, j, ranks, cd, rng)
            mating_pool.append(population[winner])
        offspring = []
        for i in range(0, len(mating_pool) - 1, 2):
            child = sbx_crossover(mating_pool[i], mating_pool[i + 1], rng)
            child = poly_mutation(child, rng)
            offspring.append(child)
        population = population + offspring
        fronts, vals, ranks, cd = evaluate(population)
        new_population = []
        for front in fronts:
            if len(new_population) + len(front) <= pop_size:
                new_population.extend(population[i] for i in front)
            else:
                sorted_front = sorted(front, key=lambda idx: cd[idx], reverse=True)
                remain = pop_size - len(new_population)
                new_population.extend(population[i] for i in sorted_front[:remain])
                break
        population = new_population
    fronts, vals, _, _ = evaluate(population)
    return [population[i] for i in fronts[0]]
