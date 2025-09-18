from __future__ import annotations

from typing import Dict, List


def _dominates(pj: Dict[str, float], pi: Dict[str, float]) -> bool:
    better_or_eq = (
        pj["Thrust"] >= pi["Thrust"]
        and pj["Isp"] >= pi["Isp"]
        and pj["Mass"] <= pi["Mass"]
        and pj["Tmax"] <= pi["Tmax"]
    )
    strictly_better = (
        pj["Thrust"] > pi["Thrust"]
        or pj["Isp"] > pi["Isp"]
        or pj["Mass"] < pi["Mass"]
        or pj["Tmax"] < pi["Tmax"]
    )
    return better_or_eq and strictly_better


def pareto_front(records: List[Dict[str, object]]) -> List[int]:
    """Compute Pareto front indices for multi-objective rocket design."""
    front: List[int] = []
    for i, rec_i in enumerate(records):
        pred_i = rec_i["pred"]  # type: ignore[index]
        dominated = False
        for j, rec_j in enumerate(records):
            if i == j:
                continue
            pred_j = rec_j["pred"]  # type: ignore[index]
            if _dominates(pred_j, pred_i):
                dominated = True
                break
        if not dominated:
            front.append(i)
    return front
