from __future__ import annotations

import math
import os
from typing import Dict


def _fake_mode() -> bool:
    if os.environ.get("ALLOW_FAKE_GEN", "1") == "1":
        return True
    path = os.environ.get("OV_SIM_XML")
    return (not path) or (not os.path.exists(path))


def predict_metrics(design: Dict[str, float]) -> Dict[str, float]:
    """Simple surrogate capturing rough rocket nozzle trends."""
    pc = float(design["Pc"])
    throat_d = float(design["throat_D"])
    area_ratio = float(design["area_ratio"])

    throat_area = math.pi * (throat_d * 0.5) ** 2
    exit_area = area_ratio * throat_area
    cf = 1.5
    thrust = cf * pc * throat_area
    isp = 300.0 + 60.0 * (area_ratio / (area_ratio + 5.0))
    tmax = 2900.0 + 300.0 * (pc / 8.0e6)

    rho = float(os.environ.get("MAT_RHO", "8190"))
    chamber_length = 0.2 + 0.6 * (area_ratio / 20.0)
    shell_thickness = 0.003
    volume = (math.pi * throat_d * 1.6 * chamber_length * shell_thickness) + (exit_area * shell_thickness)
    mass = max(1.0, rho * volume)

    sy = float(os.environ.get("MAT_SY", "1.1e9"))
    hoop = (pc * throat_d * 1.6) / max(1e-6, 2.0 * shell_thickness)
    sigma_factor = max(0.01, sy / max(1.0, hoop))

    if _fake_mode():
        thrust *= 0.9
        isp *= 0.95
        tmax *= 0.95

    return {
        "Thrust": thrust,
        "Isp": isp,
        "Tmax": tmax,
        "Mass": mass,
        "sigma": sigma_factor,
    }
