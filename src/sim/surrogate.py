from __future__ import annotations

import math
import os
from typing import Dict


def _fake_mode() -> bool:
    if os.environ.get("ALLOW_FAKE_GEN", "1") == "1":
        return True
    path = os.environ.get("OV_SIM_XML")
    return not path or not os.path.exists(path)


def predict_metrics(design: Dict[str, float]) -> Dict[str, float]:
    """
    간이 surrogate:
    Thrust ~ C_f * Pc * A_t
    Isp ~ 300 + 60 * f(Ae/At)
    Tmax ~ 2900..3300K 근사
    Mass ~ 부피*밀도(러프)
    """

    fake = _fake_mode()
    if not fake:
        # 실제 OV surrogate 연결 지점 (현재는 동일 계산 유지)
        pass

    pc = float(design["Pc"])
    throat_d = float(design["throat_D"])
    area_ratio = float(design["area_ratio"])
    area_throat = math.pi * (throat_d * 0.5) ** 2
    area_exit = area_ratio * area_throat
    cf = 1.5
    thrust = cf * pc * area_throat
    isp = 300.0 + 60.0 * (area_ratio / (area_ratio + 5.0))
    t_max = 2900.0 + 300.0 * (pc / 8.0e6)
    density = float(os.environ.get("MAT_RHO", "8190"))
    length = 0.2 + 0.6 * (area_ratio / 20.0)
    shell = 0.003
    volume = (math.pi * (throat_d * 1.6) * length * shell) + (area_exit * shell)
    mass = max(1.0, density * volume)
    yield_strength = float(os.environ.get("MAT_SY", "1.1e9"))
    hoop = (pc * (throat_d * 1.6)) / max(1e-6, 2.0 * shell)
    sigma_factor = max(0.01, yield_strength / max(1.0, hoop))
    return {
        "Thrust": thrust,
        "Isp": isp,
        "Tmax": t_max,
        "Mass": mass,
        "sigma": sigma_factor,
    }
