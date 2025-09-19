"""Evaluate pencil turbofan designs with coarse cycle proxies."""

from __future__ import annotations

import math
from typing import Dict, List

from .physics import (
    GAM,
    G0,
    R,
    comp_T_ratio_from_PR,
    fuel_to_Tt4,
    isa_t_p,
    nozzle_exit_velocity,
    stag_P_from_M,
    stag_T_from_M,
    turb_PR_from_Tdrop,
)


def evaluate_batch(designs: List[Dict[str, float]]) -> List[Dict[str, float]]:
    """Return proxy performance metrics for each design."""

    results: List[Dict[str, float]] = []
    for design in designs:
        M0 = float(design["M0"])
        alt = float(design["alt_m"])
        BPR = float(design["BPR"])
        PRc = float(design["PRc"])
        PRf = float(design["PRf"])
        eta_c = float(design["eta_c"])
        eta_f = float(design["eta_f"])
        eta_t = float(design["eta_t"])
        eta_m = float(design["eta_m"])
        pi_d = float(design["pi_d"])
        pi_b = float(design["pi_b"])
        Tt4 = float(design["Tt4"])
        m_core = float(design["m_core"])

        T0, Pa = isa_t_p(alt)
        a0 = math.sqrt(GAM * R * T0)
        V0 = M0 * a0
        Tt0 = stag_T_from_M(T0, M0)
        Pt0 = stag_P_from_M(Pa, M0) * pi_d

        tau_f = comp_T_ratio_from_PR(PRf, eta_f)
        tau_c = comp_T_ratio_from_PR(PRc, eta_c)
        Tt2 = Tt0
        Tt13 = Tt2 * tau_f
        Tt3 = Tt2 * tau_c

        fuel_ratio = fuel_to_Tt4(Tt3, Tt4)

        dT_c = Tt3 - Tt2
        dT_f = Tt13 - Tt2
        power_ratio = (dT_c + dT_f * (1.0 + BPR)) / max(eta_m, 1e-3)
        Tt5 = max(Tt4 - power_ratio / max(eta_t, 1e-3), 1.0)

        Pt2 = Pt0
        Pt13 = Pt2 * PRf
        Pt3 = Pt2 * PRc
        Pt4 = Pt3 * pi_b
        Pt5 = Pt4 / max(turb_PR_from_Tdrop(power_ratio, Tt4, eta_t), 1e-6)

        V9, _ = nozzle_exit_velocity(Tt5, Pt5, Pa)
        V19, _ = nozzle_exit_velocity(Tt13, Pt13, Pa)

        m_bypass = BPR * m_core
        m_total = m_core + m_bypass
        m_fuel = fuel_ratio * m_core

        thrust = m_core * (V9 - V0) + m_bypass * (V19 - V0)
        tsfc = m_fuel / max(thrust, 1e-6)
        isp = thrust / max(m_fuel * G0, 1e-6)
        spec_thrust = thrust / max(m_total, 1e-6)

        ok = (
            Tt4 <= 2100.0
            and Tt3 <= 950.0
            and 1.15 <= PRf <= 2.0
            and 10.0 <= PRc <= 40.0
            and 0.0 < fuel_ratio < 0.07
            and thrust > 0.0
            and tsfc < 0.0025
        )

        score = spec_thrust - 2000.0 * tsfc

        results.append(
            {
                "ok": bool(ok),
                "score": float(score),
                "F_N": float(thrust),
                "TSFC_kg_per_Ns": float(tsfc),
                "Isp_s": float(isp),
                "spec_thrust_N_per_kgps": float(spec_thrust),
                "M0": M0,
                "alt_m": alt,
                "BPR": BPR,
                "PRc": PRc,
                "PRf": PRf,
                "Tt4_K": Tt4,
                "f_fuel": float(fuel_ratio),
                "V0": float(V0),
                "V9": float(V9),
                "V19": float(V19),
                "design": design,
            }
        )
    return results
