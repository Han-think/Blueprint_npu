"""Lightweight Brayton-cycle proxies for a low-bypass turbofan."""

from __future__ import annotations

import math

from typing import Tuple

G0: float = 9.80665
"""Standard gravity [m/s^2]."""

R: float = 287.0
"""Specific gas constant for air [J/(kg·K)]."""

GAM: float = 1.4
"""Heat capacity ratio for air."""

CP: float = GAM * R / (GAM - 1.0)
"""Specific heat at constant pressure for air [J/(kg·K)]."""

LHV: float = 43e6
"""Approximate lower heating value of kerosene [J/kg]."""

EPS_TINY: float = 1e-9
"""Small value used to avoid division by zero."""


def isa_t_p(alt_m: float) -> Tuple[float, float]:
    """Return ISA static temperature and pressure for a given altitude."""

    if alt_m < 0.0:
        alt_m = 0.0

    if alt_m < 11_000.0:
        lapse = -0.0065
        t = 288.15 + lapse * alt_m
        exponent = -G0 / (lapse * R)
        p = 101_325.0 * (t / 288.15) ** exponent
    else:
        t = 216.65
        p11 = 22_632.06
        p = p11 * math.exp(-G0 * (alt_m - 11_000.0) / (R * t))
    return t, p


def stag_T_from_M(t_static: float, mach: float, gam: float = GAM) -> float:
    """Compute total temperature from static temperature and Mach number."""

    return t_static * (1.0 + 0.5 * (gam - 1.0) * mach * mach)


def stag_P_from_M(p_static: float, mach: float, gam: float = GAM) -> float:
    """Compute total pressure from static pressure and Mach number."""

    return p_static * (1.0 + 0.5 * (gam - 1.0) * mach * mach) ** (gam / (gam - 1.0))


def comp_T_ratio_from_PR(pr: float, eta_c: float, gam: float = GAM) -> float:
    """Convert a compressor pressure ratio into an approximate temperature ratio."""

    pr_exp = (gam - 1.0) / gam
    return 1.0 + (pr**pr_exp - 1.0) / max(eta_c, 1e-3)


def turb_PR_from_Tdrop(t_drop: float, t_in: float, eta_t: float, gam: float = GAM) -> float:
    """Estimate turbine pressure ratio from an enthalpy drop."""

    tau_t = max(1.0 - t_drop / max(t_in, 1e-6) / max(eta_t, 1e-3), 1e-3)
    pr_exp = gam / (gam - 1.0)
    return max(tau_t**pr_exp, 1e-3)


def nozzle_exit_velocity(t_total: float, p_total: float, p_ambient: float, gam: float = GAM) -> Tuple[float, float]:
    """Compute nozzle exit velocity and pressure for a simple converging nozzle."""

    if p_total <= 0.0:
        return 0.0, p_ambient

    pr_crit = ((gam + 1.0) / 2.0) ** (gam / (gam - 1.0))
    if p_total / max(p_ambient, EPS_TINY) <= pr_crit + EPS_TINY:
        t_exit = t_total * (p_ambient / max(p_total, EPS_TINY)) ** ((gam - 1.0) / gam)
        v_exit = math.sqrt(max(2.0 * CP * (t_total - t_exit), 0.0))
        p_exit = p_ambient
    else:
        t_exit = t_total * 2.0 / (gam + 1.0)
        v_exit = math.sqrt(max(gam * R * t_exit, 0.0))
        p_exit = p_total / pr_crit
    return v_exit, p_exit


def fuel_to_Tt4(t3: float, t4: float, eta_b: float = 0.98) -> float:
    """Compute the fuel-to-air ratio required to reach a target turbine inlet temperature."""

    delta_t = max(t4 - t3, 0.0)
    return (CP * delta_t) / (max(eta_b, 1e-3) * LHV)
