"""Helper routines to assemble rocket stacks and pencil engine summaries."""

from __future__ import annotations

import math

from typing import Any, Dict, List, Optional

from pencil.pipeline import PencilPipeline
from rocket.pipeline import RocketPipeline

G0 = 9.80665


def _stage_losses(F_N: float, Isp_s: float, prop_mass_kg: float, m0_kg: float, twr: float) -> Dict[str, float]:
    """Estimate simple gravity and drag losses for a stage burn."""

    mdot = F_N / max(Isp_s * G0, 1e-6)
    burn_time = prop_mass_kg / max(mdot, 1e-6)
    k_g = max(0.15, min(0.35, 0.5 / (max(twr, 1.05) - 1.0 + 1e-3)))
    loss_g = G0 * burn_time * k_g
    loss_d = 40.0 * burn_time / max(twr, 1.2)
    return {
        "t_burn_s": burn_time,
        "loss_g": loss_g,
        "loss_d": loss_d,
        "loss_total": loss_g + loss_d,
    }


def _pick_best_rocket(samples: int, topk: int) -> Dict[str, Any]:
    """Return the highest-Isp rocket candidate from the proxy pipeline."""

    pipeline = RocketPipeline()
    candidates = pipeline.optimize(samples=samples, topk=topk, pa_kpa=101.325, seed=123)
    if not candidates:
        raise ValueError("rocket pipeline produced no candidates")
    return max(candidates, key=lambda item: item.get("Isp_s", float("-inf")))


def _pick_best_pencil(samples: int, topk: int, M0: float, alt_m: float) -> Dict[str, Any]:
    """Return the best pencil engine candidate prioritizing feasible scores."""

    pipeline = PencilPipeline()
    candidates = pipeline.optimize(samples=samples, topk=topk, seed=123, M0=M0, alt_m=alt_m)
    if not candidates:
        raise ValueError("pencil pipeline produced no candidates")
    return max(candidates, key=lambda item: (bool(item.get("ok")), item.get("score", float("-inf"))))


def build_rocket_assembly(cfg: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Construct a stacked rocket summary using the rocket pipeline."""

    if not cfg:
        return None

    payload_mass = float(cfg.get("payload_mass", 0.0))
    stages_cfg: List[Dict[str, Any]] = list(cfg.get("stages", []))
    if not stages_cfg:
        return {
            "stages": [],
            "total_dV_m_s": 0.0,
            "total_dV_eff_m_s": 0.0,
            "min_TWR": math.inf,
            "payload_final_kg": payload_mass,
        }

    stages: List[Dict[str, Any]] = []
    running_payload = payload_mass
    total_delta_v = 0.0
    total_delta_v_eff = 0.0
    min_twr = math.inf

    for stage_cfg in stages_cfg:
        best = _pick_best_rocket(int(stage_cfg.get("samples", 256)), int(stage_cfg.get("topk", 16)))
        isp = float(best.get("Isp_s", 0.0))
        thrust = float(best.get("F_N", 0.0))
        prop_mass = float(stage_cfg.get("prop_mass", 0.0))
        dry_mass = float(stage_cfg.get("dry_mass", 0.0))

        m0 = prop_mass + dry_mass + running_payload
        mf = dry_mass + running_payload
        mass_ratio = max(m0 / max(mf, 1e-6), 1.0)
        delta_v = isp * G0 * math.log(mass_ratio)
        twr = thrust / max(m0 * G0, 1e-6)

        losses = _stage_losses(F_N=thrust, Isp_s=isp, prop_mass_kg=prop_mass, m0_kg=m0, twr=twr)
        delta_v_eff = max(delta_v - losses["loss_total"], 0.0)

        total_delta_v += delta_v
        total_delta_v_eff += delta_v_eff
        min_twr = min(min_twr, twr)

        stages.append(
            {
                "name": stage_cfg.get("name", "stage"),
                "Isp_s": isp,
                "F_N": thrust,
                "m0_kg": m0,
                "mf_kg": mf,
                "prop_mass_kg": prop_mass,
                "dry_mass_kg": dry_mass,
                "payload_in_kg": running_payload,
                "dV_m_s": delta_v,
                "dV_eff_m_s": delta_v_eff,
                "loss_g_m_s": losses["loss_g"],
                "loss_d_m_s": losses["loss_d"],
                "burn_time_s": losses["t_burn_s"],
                "TWR": twr,
                "engine": best,
            }
        )

        running_payload = mf

    return {
        "stages": stages,
        "total_dV_m_s": total_delta_v,
        "total_dV_eff_m_s": total_delta_v_eff,
        "min_TWR": min_twr,
        "payload_final_kg": running_payload,
    }


def _ramjet_boost(metric: Dict[str, Any], M0: float, cfg: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Apply a simple ramjet boost proxy to a pencil metric dictionary."""

    if not cfg or not cfg.get("enable", False):
        return dict(metric)

    turn_on = float(cfg.get("M_on", 1.8))
    gain = float(cfg.get("gain_pct", 15.0)) / 100.0
    updated = dict(metric)

    if M0 >= turn_on:
        updated["F_N"] = float(updated.get("F_N", 0.0)) * (1.0 + gain)
        spec = float(updated.get("spec_thrust_N_per_kgps", 0.0)) * (1.0 + gain)
        updated["spec_thrust_N_per_kgps"] = spec
        tsfc = float(updated.get("TSFC_kg_per_Ns", 0.0)) * 1.05
        updated["TSFC_kg_per_Ns"] = tsfc
        updated["score"] = spec - 2000.0 * tsfc

    return updated


def build_pencil_assembly(cfg: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Summarize the best pencil turbofan candidate with airframe context."""

    if not cfg:
        return None

    M0 = float(cfg.get("M0", 0.9))
    alt_m = float(cfg.get("alt_m", 2000.0))
    best = _pick_best_pencil(int(cfg.get("samples", 256)), int(cfg.get("topk", 16)), M0=M0, alt_m=alt_m)
    boosted = _ramjet_boost(best, M0, cfg.get("ramjet_boost"))

    airframe_cfg = cfg.get("airframe", {"mass_kg": 11_000.0, "fuel_kg": 3_000.0})
    mass_air = float(airframe_cfg.get("mass_kg", 11_000.0))
    mass_fuel = float(airframe_cfg.get("fuel_kg", 3_000.0))

    thrust = float(boosted.get("F_N", 0.0))
    twr = thrust / max((mass_air + mass_fuel) * G0, 1e-6)

    tsfc = float(boosted.get("TSFC_kg_per_Ns", 0.0))
    endurance = mass_fuel / max(tsfc * thrust, 1e-9)

    return {
        "engine": boosted,
        "airframe": {"mass_kg": mass_air, "fuel_kg": mass_fuel},
        "TWR": twr,
        "endurance_s_proxy": endurance,
        "flight": {"M0": M0, "alt_m": alt_m},
    }


def build_hybrid_summary(
    rocket_result: Optional[Dict[str, Any]],
    pencil_result: Optional[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """Combine rocket and pencil summaries when both subsystems are available."""

    if not (rocket_result and pencil_result):
        return None

    return {
        "note": "independent subsystems summary",
        "rocket_total_dV_m_s": float(
            rocket_result.get("total_dV_eff_m_s", rocket_result.get("total_dV_m_s", 0.0))
        ),
        "fighter_TWR": float(pencil_result.get("TWR", 0.0)),
        "fighter_endurance_s_proxy": float(pencil_result.get("endurance_s_proxy", 0.0)),
    }


__all__ = [
    "build_hybrid_summary",
    "build_pencil_assembly",
    "build_rocket_assembly",
]
