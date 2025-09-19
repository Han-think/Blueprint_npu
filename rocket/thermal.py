from __future__ import annotations

import math


def bartz_flux_proxy(Pc: float, rt_m: float, Tc: float) -> float:
    c_val = 0.06
    return c_val * (Pc ** 0.8) * (rt_m ** -0.2) * ((max(Tc, 1.0) / 3000.0) ** 0.1)


def regen_dp_proxy(mdot_cool: float, A_channels: float, L_over_D: float = 200.0) -> float:
    rho = 900.0
    velocity = (mdot_cool / max(rho, 1e-6)) / max(A_channels, 1e-9)
    friction = 0.02
    coeff = 0.5 * rho * friction
    return coeff * (velocity ** 2) * L_over_D
