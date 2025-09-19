from __future__ import annotations

import math

G0 = 9.80665


def area_from_radius(rt_m: float) -> float:
    return math.pi * rt_m * rt_m


def mach_from_area_ratio_supersonic(eps: float, gamma: float, iterations: int = 60) -> float:
    def area_ratio(mach: float) -> float:
        gm1 = gamma - 1.0
        term = (2.0 / gamma) * (1.0 + 0.5 * gm1 * mach * mach)
        return (1.0 / mach) * term ** ((gamma + 1.0) / (2.0 * gm1))

    lo, hi = 1.01, 10.0
    for _ in range(iterations):
        mid = 0.5 * (lo + hi)
        if area_ratio(mid) < eps:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def pressure_ratio_from_M(mach: float, gamma: float) -> float:
    return (1.0 + 0.5 * (gamma - 1.0) * mach * mach) ** (-gamma / (gamma - 1.0))


def c_star(gamma: float, R: float, Tc: float) -> float:
    term = gamma * (2.0 / (gamma + 1.0)) ** ((gamma + 1.0) / (2.0 * (gamma - 1.0)))
    return math.sqrt(R * Tc) / term


def thrust_coeff(gamma: float, eps: float, PePc: float, PaPc: float) -> float:
    term1 = (2.0 * gamma * gamma / (gamma - 1.0)) * (
        (2.0 / (gamma + 1.0)) ** ((gamma + 1.0) / (gamma - 1.0))
    )
    cf_ideal = math.sqrt(term1 * (1.0 - (PePc) ** ((gamma - 1.0) / gamma)))
    return cf_ideal + eps * (PePc - PaPc)


def isp_from_cf(Cf: float, Pc: float, At: float, mdot: float) -> float:
    return (Cf * Pc * At) / (mdot * G0)
