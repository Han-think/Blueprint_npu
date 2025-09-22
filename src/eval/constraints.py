from __future__ import annotations

from typing import Dict


def check_constraints(design: Dict[str, float], pred: Dict[str, float]) -> Dict[str, object]:
    t_max_limit = 1100.0  # 벽온도 한계(예시)
    sigma_min = 1.2
    ok = True
    margins = {}
    if "Tmax" in pred:
        margins["Tmax"] = t_max_limit - float(pred["Tmax"])
        ok = ok and float(pred["Tmax"]) <= t_max_limit
    if "sigma" in pred:
        margins["sigma"] = float(pred["sigma"]) - sigma_min
        ok = ok and float(pred["sigma"]) >= sigma_min
    return {"feasible": bool(ok), "margins": margins}
