from __future__ import annotations

import math
from typing import Any, Dict, Optional

import math
from typing import Any, Dict, Optional

from pencil.pipeline import PencilPipeline
from rocket.pipeline import RocketPipeline
from rocket.physics import G0


def _pick_best_rocket(samples: int, topk: int):
    pipeline = RocketPipeline()
    candidates = pipeline.optimize(samples=samples, topk=topk, pa_kpa=101.325, seed=123)
    return max(candidates, key=lambda item: item["Isp_s"])


def _pick_best_pencil(samples: int, topk: int, M0: float, alt_m: float):
    pipeline = PencilPipeline()
    candidates = pipeline.optimize(samples=samples, topk=topk, seed=123, M0=M0, alt_m=alt_m)
    return max(candidates, key=lambda item: (item["ok"], item["score"]))


def _stage_losses(F_N: float, Isp_s: float, prop_mass_kg: float, m0_kg: float, twr: float) -> dict:
    mdot = F_N / max(Isp_s * G0, 1e-6)
    burn = prop_mass_kg / max(mdot, 1e-6)
    gravity_factor = max(0.15, min(0.35, 0.5 / (max(twr, 1.05) - 1.0 + 1e-3)))
    gravity_loss = G0 * burn * gravity_factor
    drag_loss = 40.0 * burn / max(twr, 1.2)
    return {"t_burn_s": burn, "loss_g": gravity_loss, "loss_d": drag_loss, "loss_total": gravity_loss + drag_loss}


def build_rocket_assembly(cfg: Optional[Dict[str, Any]]):
    if not cfg:
        return None
    payload = float(cfg.get("payload_mass", 0.0))
    stages = cfg.get("stages", [])
    results = []
    payload_mass = payload
    dv_total = 0.0
    twr_min = float("inf")

    for stage in stages:
        best = _pick_best_rocket(samples=int(stage.get("samples", 256)), topk=int(stage.get("topk", 16)))
        isp = float(best["Isp_s"])
        thrust = float(best["F_N"])
        prop_mass = float(stage["prop_mass"])
        dry_mass = float(stage["dry_mass"])
        m0 = prop_mass + dry_mass + payload_mass
        mf = dry_mass + payload_mass
        dv = isp * G0 * math.log(max(m0 / mf, 1.000001))
        twr = thrust / (m0 * G0)
        losses = _stage_losses(thrust, isp, prop_mass, m0, twr)
        dv_eff = max(dv - losses["loss_total"], 0.0)
        dv_total += dv_eff
        twr_min = min(twr_min, twr)
        results.append(
            {
                "name": stage.get("name", "S?"),
                "Isp_s": isp,
                "F_N": thrust,
                "m0_kg": m0,
                "mf_kg": mf,
                "prop_mass_kg": prop_mass,
                "dry_mass_kg": dry_mass,
                "payload_in_kg": payload_mass,
                "dV_m_s": dv,
                "dV_eff_m_s": dv_eff,
                "loss_g_m_s": losses["loss_g"],
                "loss_d_m_s": losses["loss_d"],
                "TWR": twr,
                "engine": best,
            }
        )
        payload_mass = mf
    return {
        "stages": results,
        "total_dV_eff_m_s": dv_total,
        "min_TWR": twr_min,
        "payload_final_kg": payload_mass,
    }


def _ramjet_boost(metric: Dict[str, Any], M0: float, cfg: Optional[Dict[str, Any]]):
    if not cfg or not cfg.get("enable", False):
        return metric
    M_on = float(cfg.get("M_on", 1.8))
    gain = float(cfg.get("gain_pct", 15.0)) / 100.0
    output = dict(metric)
    if M0 >= M_on:
        output["F_N"] *= 1.0 + gain
        output["spec_thrust_N_per_kgps"] *= 1.0 + gain
        output["TSFC_kg_per_Ns"] *= 1.0 + 0.05
        output["score"] = output["spec_thrust_N_per_kgps"] - 2000.0 * output["TSFC_kg_per_Ns"]
    return output


def build_pencil_assembly(cfg: Optional[Dict[str, Any]]):
    if not cfg:
        return None
    M0 = float(cfg.get("M0", 0.9))
    alt = float(cfg.get("alt_m", 2000.0))
    best = _pick_best_pencil(samples=int(cfg.get("samples", 256)), topk=int(cfg.get("topk", 16)), M0=M0, alt_m=alt)
    best = _ramjet_boost(best, M0, cfg.get("ramjet_boost"))

    airframe = cfg.get("airframe", {"mass_kg": 11000.0, "fuel_kg": 3000.0})
    air_mass = float(airframe.get("mass_kg", 11000.0))
    fuel_mass = float(airframe.get("fuel_kg", 3000.0))
    thrust = float(best["F_N"])
    twr = thrust / ((air_mass + fuel_mass) * G0)
    tsfc = float(best["TSFC_kg_per_Ns"])
    endurance = fuel_mass / max(tsfc * thrust, 1e-9)

    return {
        "engine": best,
        "airframe": {"mass_kg": air_mass, "fuel_kg": fuel_mass},
        "TWR": twr,
        "endurance_s_proxy": endurance,
        "flight": {"M0": M0, "alt_m": alt},
    }


def build_hybrid_summary(rocket_res, pencil_res):
    if rocket_res and pencil_res:
        return {
            "note": "independent subsystems summary",
            "rocket_total_dV_m_s": rocket_res["total_dV_eff_m_s"],
            "fighter_TWR": pencil_res["TWR"],
            "fighter_endurance_s_proxy": pencil_res["endurance_s_proxy"],
        }
    return None
