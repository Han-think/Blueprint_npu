from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import json

from rocket.physics import (
    area_from_radius,
    c_star,
    mach_from_area_ratio_supersonic,
    pressure_ratio_from_M,
    thrust_coeff,
    isp_from_cf,
)
from rocket.thermal import bartz_flux_proxy, regen_dp_proxy


def _calibration():
    cfg = Path("data/cea_calib.json")
    if cfg.is_file():
        try:
            data = json.loads(cfg.read_text(encoding="utf-8"))
            return (
                float(data.get("q_bartz_scale", 1.0)),
                float(data.get("dp_regen_scale", 1.0)),
                float(data.get("isp_scale", 1.0)),
            )
        except Exception:  # pragma: no cover - defensive
            return 1.0, 1.0, 1.0
    return 1.0, 1.0, 1.0


def _manufacturing_rules():
    path = Path("manufacturing/rules.json")
    if path.is_file():
        try:
            rules = json.loads(path.read_text(encoding="utf-8"))
            rocket = rules.get("rocket", {})
            return float(rocket.get("min_wall_mm", 1.2)), float(rocket.get("min_web_mm", 0.8)), float(rocket.get("r_mid_scale", 1.4))
        except Exception:  # pragma: no cover - defensive
            return 1.2, 0.8, 1.4
    return 1.2, 0.8, 1.4


def evaluate_batch(designs: List[Dict], pa_kpa: float = 101.325) -> List[Dict]:
    q_max = 12.0e6
    v_cool_min, v_cool_max = 5.0, 40.0
    dp_regen_max = 2.5e6
    rho_cool = 900.0
    results = []
    Pa = pa_kpa * 1e3

    q_scale, dp_scale, isp_scale = _calibration()
    min_wall_mm, min_web_mm, r_mid_scale = _manufacturing_rules()

    for design in designs:
        Pc = design["Pc_MPa"] * 1e6
        Tc = design["Tc_K"]
        gamma = design["gamma"]
        gas_constant = design["R"]
        rt = design["rt_mm"] * 1e-3
        eps = design["eps"]
        spike_deg = design["spike_deg"]
        film = design["film_frac"]
        cool = design["cool_frac"]
        ch_d = design["ch_d_mm"] * 1e-3
        ch_n = int(design["ch_n"])

        At = area_from_radius(rt)
        mach_exit = mach_from_area_ratio_supersonic(eps, gamma)
        PePc = pressure_ratio_from_M(mach_exit, gamma)
        PaPc = Pa / Pc
        c_star_value = c_star(gamma, gas_constant, Tc)
        mdot_total = Pc * At / c_star_value
        mdot_cool = mdot_total * cool

        Cf = thrust_coeff(gamma, eps, PePc, PaPc)
        spike_penalty = max(0.90, 1.0 - 0.003 * (spike_deg - 10.0))
        film_penalty = max(0.92, 1.0 - 0.5 * film)
        Cf_eff = Cf * spike_penalty * film_penalty

        thrust = Cf_eff * Pc * At
        isp = isp_from_cf(Cf_eff, Pc, At, mdot_total) * isp_scale

        q_bartz = bartz_flux_proxy(Pc=Pc, rt_m=rt, Tc=Tc) * q_scale
        channel_area = ch_n * (3.14159 * (ch_d ** 2) / 4.0)
        v_cool = (mdot_cool / rho_cool) / max(channel_area, 1e-8)
        dp_regen = regen_dp_proxy(mdot_cool=mdot_cool, A_channels=channel_area) * dp_scale

        r_mid = r_mid_scale * rt
        pitch = 2.0 * 3.14159 * r_mid / max(ch_n, 1)
        web_thickness = max(pitch - ch_d, 0.0) * 1e3
        mfg_ok = (web_thickness >= min_web_mm) and (min_wall_mm >= 1.0)

        ok = (
            q_bartz <= q_max
            and v_cool_min <= v_cool <= v_cool_max
            and dp_regen <= dp_regen_max
            and 0.0 <= film <= 0.2
            and 0.04 <= cool <= 0.25
            and (film + cool) < 0.3
            and mfg_ok
        )

        score = isp - 1e-6 * q_bartz - 1e-7 * dp_regen - (0.0 if mfg_ok else 1e3)

        results.append(
            {
                "ok": bool(ok),
                "score": float(score),
                "F_N": float(thrust),
                "Isp_s": float(isp),
                "mdot_kg_s": float(mdot_total),
                "Me": float(mach_exit),
                "Pe_over_Pc": float(PePc),
                "q_bartz_W_m2": float(q_bartz),
                "dp_regen_Pa": float(dp_regen),
                "v_cool_m_s": float(v_cool),
                "web_thickness_mm": float(web_thickness),
                "mfg_ok": bool(mfg_ok),
                "design": design,
            }
        )
    return results
