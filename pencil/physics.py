from __future__ import annotations

import math

G0 = 9.80665
R = 287.0
GAM = 1.4
CP = GAM * R / (GAM - 1.0)
LHV = 43e6
EPS_TINY = 1e-9


def isa_t_p(alt_m: float):
    if alt_m < 11_000.0:
        temperature = 288.15 - 0.0065 * alt_m
        pressure = 101_325.0 * (temperature / 288.15) ** (GAM * R / (-0.0065 * R))
    else:
        temperature = 216.65
        base = 22632.06
        pressure = base * math.exp(-G0 * (alt_m - 11_000.0) / (R * temperature))
    return temperature, pressure


def stag_T_from_M(T0: float, M: float, gam: float = GAM):
    return T0 * (1.0 + 0.5 * (gam - 1.0) * M * M)


def stag_P_from_M(P0: float, M: float, gam: float = GAM):
    return P0 * (1.0 + 0.5 * (gam - 1.0) * M * M) ** (gam / (gam - 1.0))


def comp_T_ratio_from_PR(PR: float, eta_c: float, gam: float = GAM):
    exponent = (gam - 1.0) / gam
    return 1.0 + (PR ** exponent - 1.0) / max(eta_c, 1e-3)


def turb_PR_from_Tdrop(t_drop: float, T_in: float, eta_t: float, gam: float = GAM):
    tau_t = max(1.0 - t_drop / max(T_in, 1e-6) / max(eta_t, 1e-3), 1e-3)
    exponent = gam / (gam - 1.0)
    return max(tau_t ** exponent, 1e-3)


def nozzle_exit_velocity(Tt_in: float, Pt_in: float, Pa: float, gam: float = GAM):
    pr_crit = ((gam + 1.0) / 2.0) ** (gam / (gam - 1.0))
    if Pt_in / Pa <= pr_crit + EPS_TINY:
        Te = Tt_in * (Pa / Pt_in) ** ((gam - 1.0) / gam)
        velocity = math.sqrt(max(2.0 * CP * (Tt_in - Te), 0.0))
    else:
        Te = Tt_in * 2.0 / (gam + 1.0)
        velocity = math.sqrt(max(gam * R * Te, 0.0))
    return velocity, Pa


def fuel_to_Tt4(Tt3: float, Tt4: float, eta_b: float = 0.98):
    delta_T = max(Tt4 - Tt3, 0.0)
    return (CP * delta_T) / (max(eta_b, 1e-3) * LHV)
