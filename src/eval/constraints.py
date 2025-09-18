from __future__ import annotations

from typing import Dict


def check_constraints(design: Dict[str, float], pred: Dict[str, float]) -> Dict[str, object]:
    tmax_limit = 1100.0
    sigma_min = 1.2
    feasible = True
    margins: Dict[str, float] = {}

    if "Tmax" in pred:
        margins["Tmax"] = tmax_limit - float(pred["Tmax"])
        feasible = feasible and (float(pred["Tmax"]) <= tmax_limit)
    if "sigma" in pred:
        margins["sigma"] = float(pred["sigma"]) - sigma_min
        feasible = feasible and (float(pred["sigma"]) >= sigma_min)

    return {"feasible": bool(feasible), "margins": margins}
