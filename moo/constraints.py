"""Constraint proxy helpers for multi-objective optimisation."""

from __future__ import annotations

from typing import Dict


def rocket_violation(metrics: Dict) -> float:
    """Return a summed violation score for rocket optimisation metrics.

    The score is zero when all constraints are satisfied and increases with the
    magnitude of violations. The thresholds mirror the limits used by the
    rocket evaluator so Deb-style constraint handling can be applied inside the
    optimiser.
    """

    violation = 0.0
    q_max = 12.0e6
    if metrics["q_bartz_W_m2"] > q_max:
        violation += (metrics["q_bartz_W_m2"] - q_max) / q_max

    if metrics["v_cool_m_s"] < 5.0:
        violation += (5.0 - metrics["v_cool_m_s"]) / 5.0
    if metrics["v_cool_m_s"] > 40.0:
        violation += (metrics["v_cool_m_s"] - 40.0) / 40.0

    dp_max = 2.5e6
    if metrics["dp_regen_Pa"] > dp_max:
        violation += (metrics["dp_regen_Pa"] - dp_max) / dp_max

    web_thickness = metrics.get("web_thickness_mm")
    if web_thickness is not None and web_thickness < 0.8:
        violation += (0.8 - web_thickness) / 0.8

    return float(max(violation, 0.0))


def pencil_violation(metrics: Dict) -> float:
    """Return a coarse violation score for pencil optimisation metrics."""

    violation = 0.0
    if metrics["TSFC_kg_per_Ns"] <= 0.0:
        violation += 1.0
    if metrics["spec_thrust_N_per_kgps"] <= 0.0:
        violation += 1.0

    fuel_fraction = metrics.get("f_fuel")
    if fuel_fraction is not None and not (0.0 < fuel_fraction < 1.0):
        violation += 0.5

    return float(max(violation, 0.0))
