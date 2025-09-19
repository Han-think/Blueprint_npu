from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Dict

MAT_PATH = Path("data/materials/rocket_alloys.json")
RULES_PATH = Path("manufacturing/rules.json")


def _materials(name: str):
    data = json.loads(MAT_PATH.read_text(encoding="utf-8"))
    return data["materials"][name]


def _rules():
    if not RULES_PATH.is_file():
        return {"rocket": {"min_wall_mm": 1.2, "r_mid_scale": 1.4}}
    return json.loads(RULES_PATH.read_text(encoding="utf-8"))


def wall_temperature_K(q_bartz_W_m2: float, h_W_m2K: float = 12_000.0, T_cool_K: float = 300.0) -> float:
    return T_cool_K + q_bartz_W_m2 / max(h_W_m2K, 1e-6)


def nozzle_shell_mass_kg(rt_m: float, eps: float, L_factor: float, t_wall_m: float, density_kg_m3: float) -> float:
    re = rt_m * math.sqrt(eps)
    length = L_factor * (re - rt_m) if re > rt_m else L_factor * rt_m
    r_mean = 0.5 * (rt_m + re)
    area = 2.0 * math.pi * r_mean * length
    volume = area * max(t_wall_m, 1e-6)
    return density_kg_m3 * volume


def evaluate_material(design: Dict, metric: Dict, material: str = "Inconel718") -> Dict:
    mat = _materials(material)
    rules = _rules()["rocket"]
    rt = design["rt_mm"] * 1e-3
    eps = design["eps"]
    thickness_mm = max(rules.get("min_wall_mm", 1.2), 1.0)
    thickness_m = thickness_mm * 1e-3

    T_wall = wall_temperature_K(metric["q_bartz_W_m2"])
    thermal_ok = T_wall <= float(mat["T_allow_K"])

    mass = nozzle_shell_mass_kg(rt, eps, L_factor=8.0, t_wall_m=thickness_m, density_kg_m3=float(mat["rho_kg_m3"]))
    cost = mass * float(mat["cost_usd_kg"])
    margin = float(mat["T_allow_K"]) - T_wall

    return {
        "material": material,
        "T_wall_K": T_wall,
        "T_allow_K": float(mat["T_allow_K"]),
        "thermal_ok": bool(thermal_ok),
        "margin_K": margin,
        "mass_kg": mass,
        "cost_usd": cost,
    }
