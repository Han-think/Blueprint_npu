"""Lightweight NSGA-II implementation for multi-objective optimisation."""
from __future__ import annotations

from typing import Callable, Dict, List, Sequence, Tuple
import math
import random


def _dominates(a: Sequence[float], b: Sequence[float], minimize: Sequence[bool]) -> bool:
    better_or_equal = True
    strictly_better = False
    for ai, bi, is_min in zip(a, b, minimize):
        if is_min:
            if ai > bi:
                better_or_equal = False
            if ai < bi:
                strictly_better = True
        else:
            if ai < bi:
                better_or_equal = False
            if ai > bi:
                strictly_better = True
    return better_or_equal and strictly_better


def fast_non_dominated_sort(values: List[Sequence[float]], minimize: Sequence[bool]) -> List[List[int]]:
    N = len(values)
    dominates: List[List[int]] = [[] for _ in range(N)]
    domination_count = [0] * N
    rank = [math.inf] * N
    fronts: List[List[int]] = [[]]

    for p in range(N):
        dominated = []
        np_count = 0
        for q in range(N):
            if _dominates(values[p], values[q], minimize):
                dominated.append(q)
            elif _dominates(values[q], values[p], minimize):
                np_count += 1
        dominates[p] = dominated
        domination_count[p] = np_count
        if np_count == 0:
            rank[p] = 0
            fronts[0].append(p)

    i = 0
    while fronts[i]:
        next_front: List[int] = []
        for p in fronts[i]:
            for q in dominates[p]:
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
    if len(indices) <= 2:
        return {i: float("inf") for i in indices}

    distances = {i: 0.0 for i in indices}
    num_obj = len(values[0])

    for m in range(num_obj):
        sorted_idx = sorted(indices, key=lambda i: values[i][m])
        if not minimize[m]:
            sorted_idx = list(reversed(sorted_idx))
        f_min = values[sorted_idx[0]][m]
        f_max = values[sorted_idx[-1]][m]
        distances[sorted_idx[0]] = float("inf")
        distances[sorted_idx[-1]] = float("inf")
        denom = f_max - f_min if abs(f_max - f_min) > 1e-12 else 1.0
        for pos in range(1, len(sorted_idx) - 1):
            prev_idx = sorted_idx[pos - 1]
            next_idx = sorted_idx[pos + 1]
            distances[sorted_idx[pos]] += (values[next_idx][m] - values[prev_idx][m]) / denom
    return distances


def _tournament(a: int, b: int, ranks: Dict[int, int], cd: Dict[int, float]) -> int:
    if ranks[a] < ranks[b]:
        return a
    if ranks[b] < ranks[a]:
        return b
    return a if cd[a] >= cd[b] else b


def sbx_crossover(parent_a: Dict, parent_b: Dict, rng: random.Random, eta: float = 10.0, probability: float = 0.9) -> Dict:
    if rng.random() > probability:
        return dict(parent_a if rng.random() < 0.5 else parent_b)

    child: Dict = {}
    for key in parent_a.keys():
        va = parent_a[key]
        vb = parent_b[key]
        if not isinstance(va, (int, float)) or not isinstance(vb, (int, float)):
            child[key] = rng.choice([va, vb])
            continue
        if va == vb:
            child[key] = va
            continue
        lower, upper = (va, vb) if va < vb else (vb, va)
        u = rng.random()
        if u <= 0.5:
            beta = (2 * u) ** (1.0 / (eta + 1.0))
        else:
            beta = (1.0 / (2.0 * (1.0 - u))) ** (1.0 / (eta + 1.0))
        value = 0.5 * ((1 + beta) * va + (1 - beta) * vb)
        span = upper - lower
        lo = lower - 0.25 * span
        hi = upper + 0.25 * span
        child[key] = min(max(value, lo), hi)
    return child


def poly_mutation(solution: Dict, rng: random.Random, eta: float = 12.0, probability: float = 0.15) -> Dict:
    mutated = dict(solution)
    for key, value in solution.items():
        if isinstance(value, (int, float)) and rng.random() < probability:
            u = rng.random()
            if u < 0.5:
                delta = (2 * u) ** (1.0 / (eta + 1.0)) - 1.0
            else:
                delta = 1.0 - (2 * (1 - u)) ** (1.0 / (eta + 1.0))
            mutated[key] = value * (1.0 + 0.15 * delta)
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
        vals = [objective(candidate) for candidate in pop]
        fronts = fast_non_dominated_sort(vals, minimize)
        ranks: Dict[int, int] = {}
        for rank_idx, front in enumerate(fronts):
            for idx in front:
                ranks[idx] = rank_idx
        distances: Dict[int, float] = {}
        for front in fronts:
            distances.update(crowding_distance(front, vals, minimize))
        return fronts, vals, ranks, distances

    for _ in range(generations):
        fronts, values, ranks, distances = evaluate(population)

        mating_pool: List[Dict] = []
        while len(mating_pool) < len(population):
            ia = rng.randrange(len(population))
            ib = rng.randrange(len(population))
            winner = _tournament(ia, ib, ranks, distances)
            mating_pool.append(population[winner])

        offspring: List[Dict] = []
        for i in range(0, len(mating_pool) - 1, 2):
            child = sbx_crossover(mating_pool[i], mating_pool[i + 1], rng)
            child = poly_mutation(child, rng)
            offspring.append(child)

        population = population + offspring
        fronts, values, ranks, distances = evaluate(population)
        new_population: List[Dict] = []
        for front in fronts:
            if len(new_population) + len(front) <= pop_size:
                new_population.extend(population[i] for i in front)
            else:
                remaining = pop_size - len(new_population)
                front_sorted = sorted(front, key=lambda i: distances[i], reverse=True)
                new_population.extend(population[i] for i in front_sorted[:remaining])
                break
        population = new_population

    final_fronts, _, _, _ = evaluate(population)
    return [population[i] for i in final_fronts[0]]
