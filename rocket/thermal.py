"""Thermal proxy utilities for the rocket evaluator."""

from __future__ import annotations


def bartz_flux_proxy(Pc: float, rt_m: float, Tc: float) -> float:
    """Approximate convective heat flux using a Bartz-like relation."""

    scale = 0.06
    return scale * (Pc**0.8) * (rt_m**-0.2) * ((max(Tc, 1.0) / 3000.0) ** 0.1)


def regen_dp_proxy(mdot_cool: float, A_channels: float, L_over_D: float = 200.0) -> float:
    """Approximate pressure drop across regenerative cooling channels."""

    rho = 900.0
    velocity = (mdot_cool / max(rho, 1e-6)) / max(A_channels, 1e-9)
    friction_factor = 0.02
    coeff = 0.5 * rho * friction_factor
    return coeff * (velocity**2) * L_over_D
