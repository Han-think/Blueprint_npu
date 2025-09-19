from __future__ import annotations

from typing import Dict, List

from pencil.physics import (
    EPS_TINY,
    G0,
    isa_t_p,
    fuel_to_Tt4,
    nozzle_exit_velocity,
    stag_P_from_M,
    stag_T_from_M,
    comp_T_ratio_from_PR,
)


def evaluate_batch(designs: List[Dict]) -> List[Dict]:
    results = []
    for design in designs:
        M0 = design["M0"]
        alt = design["alt_m"]
        BPR = design["BPR"]
        PRc = design["PRc"]
        PRf = design["PRf"]
        eta_c = design["eta_c"]
        eta_f = design["eta_f"]
        eta_t = design["eta_t"]
        eta_m = design["eta_m"]
        pi_d = design["pi_d"]
        pi_b = design["pi_b"]
        Tt4 = design["Tt4"]
        m_core = design["m_core"]

        T0, Pa = isa_t_p(alt)
        a0 = (1.4 * 287.0 * T0) ** 0.5
        V0 = M0 * a0
        Tt0 = stag_T_from_M(T0, M0)
        Pt0 = stag_P_from_M(Pa, M0) * pi_d

        tau_f = comp_T_ratio_from_PR(PRf, eta_f)
        tau_c = comp_T_ratio_from_PR(PRc, eta_c)
        Tt2 = Tt0
        Tt13 = Tt2 * tau_f
        Tt3 = Tt2 * tau_c

        f = fuel_to_Tt4(Tt3, Tt4)

        dT_c = Tt3 - Tt2
        dT_f = Tt13 - Tt2
        power_ratio = (dT_c + dT_f * (1.0 + BPR)) / max(eta_m, 1e-3)
        Tt5 = max(Tt4 - power_ratio / max(eta_t, 1e-3), 1.0)

        Pt2 = Pt0
        Pt13 = Pt2 * PRf
        Pt3 = Pt2 * PRc
        Pt4 = Pt3 * pi_b
        Pt5 = Pt4 / max(1e-6, (Tt5 / Tt4) ** (1.4 / (1.4 - 1.0)))

        V9, _ = nozzle_exit_velocity(Tt5, Pt5, Pa)
        V19, _ = nozzle_exit_velocity(Tt13, Pt13, Pa)

        m_b = BPR * m_core
        m_total = m_core + m_b
        m_fuel = f * m_core
        thrust = m_core * (V9 - V0) + m_b * (V19 - V0)

        TSFC = m_fuel / max(thrust, 1e-6)
        isp = thrust / max(m_fuel * G0, 1e-6)
        spec_thrust = thrust / max(m_total, EPS_TINY)

        ok = (
            Tt4 <= 2_100.0
            and Tt3 <= 950.0
            and 1.15 <= PRf <= 2.0
            and 10.0 <= PRc <= 40.0
            and 0.0 < f < 0.07
            and thrust > 0.0
            and TSFC < 0.0025
        )

        score = spec_thrust - 2000.0 * TSFC

        results.append(
            {
                "ok": bool(ok),
                "score": float(score),
                "F_N": float(thrust),
                "TSFC_kg_per_Ns": float(TSFC),
                "Isp_s": float(isp),
                "spec_thrust_N_per_kgps": float(spec_thrust),
                "M0": float(M0),
                "alt_m": float(alt),
                "BPR": float(BPR),
                "PRc": float(PRc),
                "PRf": float(PRf),
                "Tt4_K": float(Tt4),
                "f_fuel": float(f),
                "V0": float(V0),
                "V9": float(V9),
                "V19": float(V19),
                "design": design,
            }
        )
    return results
