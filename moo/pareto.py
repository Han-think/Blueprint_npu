from __future__ import annotations

from typing import List, Sequence


def _dominates(a: Sequence[float], b: Sequence[float], minimize: Sequence[bool]) -> bool:
    better_or_equal = True
    strictly_better = False
    for ai, bi, minimise in zip(a, b, minimize):
        if minimise:
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


def pareto_front(objs: List[Sequence[float]], minimize: Sequence[bool]) -> List[int]:
    n = len(objs)
    dominated = [False] * n
    indices = list(range(n))
    for i in range(n):
        if dominated[i]:
            continue
        for j in range(n):
            if i == j or dominated[i]:
                continue
            if _dominates(objs[j], objs[i], minimize):
                dominated[i] = True
    return [i for i in indices if not dominated[i]]
