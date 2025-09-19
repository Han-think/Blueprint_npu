"""Evaluation utilities for rocket design candidates with thermal proxies."""

from __future__ import annotations

import math
from typing import Dict, List

from .physics import (
    area_from_radius,
    characteristic_velocity,
    isp_from_cf,
    mach_from_area_ratio_supersonic,
    pressure_ratio_from_mach,
    thrust_coefficient,
)
from .thermal import bartz_flux_proxy, regen_dp_proxy


def evaluate_batch(designs: List[Dict[str, float]], pa_kpa: float = 101.325) -> List[Dict[str, float]]:
    """Evaluate a batch of rocket designs using lightweight proxy models."""

    q_max = 12.0e6
    rho_cool = 900.0
    v_cool_min, v_cool_max = 5.0, 40.0
    dp_regen_max = 2.5e6
    results: List[Dict[str, float]] = []
    ambient_pa = pa_kpa * 1e3

    for design in designs:
        chamber_pressure = design["Pc_MPa"] * 1e6
        chamber_temp = design["Tc_K"]
        gamma = design["gamma"]
        gas_constant = design["R"]
        throat_radius = design["rt_mm"] * 1e-3
        area_ratio = design["eps"]
        spike_deg = design["spike_deg"]
        film = design["film_frac"]
        coolant_fraction = design["cool_frac"]
        channel_diameter = design["ch_d_mm"] * 1e-3
        channel_count = int(design["ch_n"])

        throat_area = area_from_radius(throat_radius)
        exit_mach = mach_from_area_ratio_supersonic(area_ratio, gamma)
        pe_over_pc = pressure_ratio_from_mach(exit_mach, gamma)
        pa_over_pc = ambient_pa / chamber_pressure

        cstar = characteristic_velocity(gamma, gas_constant, chamber_temp)
        mass_flow_total = chamber_pressure * throat_area / cstar
        mass_flow_coolant = mass_flow_total * coolant_fraction

        cf = thrust_coefficient(gamma, area_ratio, pe_over_pc, pa_over_pc)

        spike_penalty = max(0.90, 1.0 - 0.003 * (spike_deg - 10.0))
        film_penalty = max(0.92, 1.0 - 0.5 * film)
        cf_eff = cf * spike_penalty * film_penalty

        thrust = cf_eff * chamber_pressure * throat_area
        isp = isp_from_cf(cf_eff, chamber_pressure, throat_area, mass_flow_total)

        heat_flux_proxy = bartz_flux_proxy(Pc=chamber_pressure, rt_m=throat_radius, Tc=chamber_temp)
        channel_area = channel_count * (math.pi * (channel_diameter**2) / 4.0)
        coolant_velocity = (mass_flow_coolant / rho_cool) / max(channel_area, 1e-8)
        dp_regen = regen_dp_proxy(mass_flow_coolant, channel_area)

        ok = (
            heat_flux_proxy <= q_max
            and v_cool_min <= coolant_velocity <= v_cool_max
            and dp_regen <= dp_regen_max
            and 0.0 <= film <= 0.2
            and 0.04 <= coolant_fraction <= 0.25
            and (film + coolant_fraction) < 0.3
        )

        score = isp - 1e-6 * heat_flux_proxy - 1e-7 * dp_regen
        results.append(
            {
                "ok": bool(ok),
                "score": float(score),
                "F_N": float(thrust),
                "Isp_s": float(isp),
                "mdot_kg_s": float(mass_flow_total),
                "Me": float(exit_mach),
                "Pe_over_Pc": float(pe_over_pc),
                "q_bartz_W_m2": float(heat_flux_proxy),
                "dp_regen_Pa": float(dp_regen),
                "v_cool_m_s": float(coolant_velocity),
                "design": design,
            }
        )

    return results
