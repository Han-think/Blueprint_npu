"""Pareto front utilities for multi-objective optimization."""

from __future__ import annotations

from typing import List, Sequence


def _dominates(a: Sequence[float], b: Sequence[float], minimize: Sequence[bool]) -> bool:
    """Return True if objective vector ``a`` dominates ``b``."""

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


def pareto_front(objs: List[Sequence[float]], minimize: Sequence[bool]) -> List[int]:
    """Return indices corresponding to the Pareto front.

    Args:
        objs: Objective vectors for each candidate.
        minimize: Flags describing whether the corresponding objective is to be
            minimized. ``False`` values indicate maximization.
    """

    n = len(objs)
    dominated = [False] * n
    idxs = list(range(n))

    for i in range(n):
        if dominated[i]:
            continue
        for j in range(n):
            if i == j or dominated[i]:
                continue
            if _dominates(objs[j], objs[i], minimize):
                dominated[i] = True
    return [i for i in idxs if not dominated[i]]
