"""Lightweight physics proxies used by the rocket pipeline."""

from __future__ import annotations

import math



G0 = 9.80665


def area_from_radius(rt_m: float) -> float:
    """Return throat area in square metres from radius."""

    return math.pi * rt_m * rt_m


def mach_from_area_ratio_supersonic(eps: float, gamma: float, it: int = 60) -> float:
    """Solve for the supersonic Mach number that satisfies the area ratio."""

    def area_ratio(mach: float) -> float:
        gm1 = gamma - 1.0
        term = (2.0 / gamma) * (1.0 + 0.5 * gm1 * mach * mach)
        return (1.0 / mach) * term ** ((gamma + 1.0) / (2.0 * gm1))

    lo, hi = 1.01, 10.0
    for _ in range(it):
        mid = 0.5 * (lo + hi)
        if area_ratio(mid) < eps:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def pressure_ratio_from_mach(mach: float, gamma: float) -> float:
    """Isentropic pressure ratio P/P0 for a given Mach number."""

    return (1.0 + 0.5 * (gamma - 1.0) * mach * mach) ** (-gamma / (gamma - 1.0))


def characteristic_velocity(gamma: float, gas_constant: float, chamber_temp: float) -> float:
    """Return the characteristic velocity c* for an ideal gas."""

    term = gamma * (2.0 / (gamma + 1.0)) ** ((gamma + 1.0) / (2.0 * (gamma - 1.0)))
    return math.sqrt(gas_constant * chamber_temp) / term


def thrust_coefficient(gamma: float, eps: float, pe_over_pc: float, pa_over_pc: float) -> float:
    """Compute thrust coefficient including the pressure thrust contribution."""

    term1 = (
        2.0
        * gamma
        * gamma
        / (gamma - 1.0)
        * (2.0 / (gamma + 1.0)) ** ((gamma + 1.0) / (gamma - 1.0))
    )
    cf_ideal = math.sqrt(term1 * (1.0 - pe_over_pc ** ((gamma - 1.0) / gamma)))
    return cf_ideal + eps * (pe_over_pc - pa_over_pc)


def isp_from_cf(cf: float, chamber_pressure: float, throat_area: float, mass_flow: float) -> float:
    """Compute specific impulse from thrust coefficient."""

    return (cf * chamber_pressure * throat_area) / (mass_flow * G0)

