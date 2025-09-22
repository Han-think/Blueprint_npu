from __future__ import annotations

from typing import Dict, List


def pareto_front(records: List[Dict[str, object]]) -> List[int]:
    """아주 단순한 Pareto (Max Thrust/Isp, Min Mass/Tmax)."""
    indices = list(range(len(records)))
    front: List[int] = []
    for i in indices:
        metrics_i = records[i]["pred"]  # type: ignore[index]
        dominated = False
        for j in indices:
            if i == j:
                continue
            metrics_j = records[j]["pred"]  # type: ignore[index]
            better_or_equal = (
                metrics_j["Thrust"] >= metrics_i["Thrust"]
                and metrics_j["Isp"] >= metrics_i["Isp"]
                and metrics_j["Mass"] <= metrics_i["Mass"]
                and metrics_j["Tmax"] <= metrics_i["Tmax"]
            )
            strictly_better = (
                metrics_j["Thrust"] > metrics_i["Thrust"]
                or metrics_j["Isp"] > metrics_i["Isp"]
                or metrics_j["Mass"] < metrics_i["Mass"]
                or metrics_j["Tmax"] < metrics_i["Tmax"]
            )
            if better_or_equal and strictly_better:
                dominated = True
                break
        if not dominated:
            front.append(i)
    return front
