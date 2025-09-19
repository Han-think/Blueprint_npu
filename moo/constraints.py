from __future__ import annotations

from typing import Dict


def rocket_violation(metrics: Dict) -> float:
    violation = 0.0
    q_max = 12.0e6
    if metrics["q_bartz_W_m2"] > q_max:
        violation += (metrics["q_bartz_W_m2"] - q_max) / q_max
    if metrics["v_cool_m_s"] < 5.0:
        violation += (5.0 - metrics["v_cool_m_s"]) / 5.0
    if metrics["v_cool_m_s"] > 40.0:
        violation += (metrics["v_cool_m_s"] - 40.0) / 40.0
    if metrics["dp_regen_Pa"] > 2.5e6:
        violation += (metrics["dp_regen_Pa"] - 2.5e6) / 2.5e6
    if "web_thickness_mm" in metrics and metrics["web_thickness_mm"] < 0.8:
        violation += (0.8 - metrics["web_thickness_mm"]) / 0.8
    return float(max(violation, 0.0))


def pencil_violation(metrics: Dict) -> float:
    violation = 0.0
    if metrics["TSFC_kg_per_Ns"] <= 0:
        violation += 1.0
    if metrics["spec_thrust_N_per_kgps"] <= 0:
        violation += 1.0
    if "f_fuel" in metrics and not (0.0 < metrics["f_fuel"] < 1.0):
        violation += 0.5
    return float(max(violation, 0.0))
