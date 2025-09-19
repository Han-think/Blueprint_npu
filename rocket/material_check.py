"""Material suitability checks and mass/cost estimates for rocket designs."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Dict

MATERIAL_PATH = Path("data/materials/rocket_alloys.json")
RULES_PATH = Path("manufacturing/rules.json")


def _load_material(material: str) -> Dict[str, float]:
    data = json.loads(MATERIAL_PATH.read_text(encoding="utf-8"))
    try:
        return data["materials"][material]
    except KeyError as exc:  # pragma: no cover - defensive
        raise ValueError(f"unknown material: {material}") from exc


def _load_rules() -> Dict[str, float]:
    if not RULES_PATH.is_file():
        return {"min_wall_mm": 1.2, "r_mid_scale": 1.4}
    data = json.loads(RULES_PATH.read_text(encoding="utf-8"))
    return data.get("rocket", {})


def wall_temperature_K(heat_flux_w_m2: float, h_w_m2K: float = 12_000.0, coolant_K: float = 300.0) -> float:
    """Newtonian convection proxy for wall temperature."""

    return coolant_K + heat_flux_w_m2 / max(h_w_m2K, 1e-6)


def nozzle_shell_mass_kg(
    throat_radius_m: float,
    area_ratio: float,
    length_factor: float,
    wall_thickness_m: float,
    density_kg_m3: float,
) -> float:
    exit_radius = throat_radius_m * math.sqrt(area_ratio)
    length = length_factor * max(exit_radius - throat_radius_m, throat_radius_m)
    mean_radius = 0.5 * (throat_radius_m + exit_radius)
    shell_area = 2.0 * math.pi * mean_radius * length
    volume = shell_area * max(wall_thickness_m, 1e-6)
    return density_kg_m3 * volume


def evaluate_material(design: Dict[str, float], metric: Dict[str, float], material: str = "Inconel718") -> Dict[str, float]:
    mat = _load_material(material)
    rules = _load_rules()
    throat_radius_m = float(design["rt_mm"]) * 1e-3
    area_ratio = float(design["eps"])
    wall_mm = max(float(rules.get("min_wall_mm", 1.2)), 1.0)
    wall_m = wall_mm * 1e-3

    wall_temp = wall_temperature_K(float(metric["q_bartz_W_m2"]))
    allowable_temp = float(mat["T_allow_K"])
    thermal_ok = wall_temp <= allowable_temp

    mass = nozzle_shell_mass_kg(
        throat_radius_m,
        area_ratio,
        length_factor=8.0,
        wall_thickness_m=wall_m,
        density_kg_m3=float(mat["rho_kg_m3"]),
    )
    cost = mass * float(mat["cost_usd_kg"])

    return {
        "material": material,
        "T_wall_K": wall_temp,
        "T_allow_K": allowable_temp,
        "thermal_ok": bool(thermal_ok),
        "margin_K": allowable_temp - wall_temp,
        "mass_kg": mass,
        "cost_usd": cost,
    }
