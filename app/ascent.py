 codex/initialize-npu-inference-template-v1n7c2
from __future__ import annotations

from fastapi import Depends, FastAPI

"""Rocket ascent integration API."""

from __future__ import annotations

import math

from typing import Optional

from fastapi import Depends, FastAPI, HTTPException
 main
from pydantic import BaseModel

from app.security import require_api_key

 codex/initialize-npu-inference-template-v1n7c2
app = FastAPI(title="Ascent API")


class AscentRequest(BaseModel):
    mass_kg: float = 1000.0

G0 = 9.80665
R_AIR = 287.0


def _air_density(altitude_m: float) -> float:
    """Rudimentary atmospheric density model."""

    if altitude_m < 11_000.0:
        temperature = 288.15 - 0.0065 * altitude_m
        pressure = 101_325.0 * (temperature / 288.15) ** (-5.25588)
    else:
        temperature = 216.65
        pressure = 22_632.06 * math.exp(-G0 * (altitude_m - 11_000.0) / (R_AIR * temperature))
    return pressure / (R_AIR * temperature)


class AscentReq(BaseModel):
    """Ascent request."""

    preset: Optional[str] = "rocket_3stage_demo"
    CdA: float = 2.0
    dt_s: float = 0.1
    alt0_m: float = 0.0


app = FastAPI(title="Ascent API")
 main


@app.get("/ascent/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


 codex/initialize-npu-inference-template-v1n7c2
@app.post("/ascent/run")
def run(_: AscentRequest, __: None = Depends(require_api_key)) -> dict[str, float]:
    return {"max_altitude_m": 100.0}

@app.post("/ascent/rocket")
def rocket(req: AscentReq, _: None = Depends(require_api_key)) -> dict[str, object]:
    """Integrate a vertical ascent for the configured preset."""

    from importlib import import_module

    presets_module = import_module("assembly.presets")
    builder_module = import_module("assembly.builder")
    PRESETS = getattr(presets_module, "PRESETS")
    _pick_best_rocket = getattr(builder_module, "_pick_best_rocket")

    if req.preset not in PRESETS:
        raise HTTPException(status_code=404, detail="unknown preset")
    preset_cfg = PRESETS[req.preset].get("rocket")
    if not preset_cfg:
        raise HTTPException(status_code=400, detail="preset missing rocket configuration")

    stages_cfg = list(preset_cfg.get("stages", []))
    payload_mass = float(preset_cfg.get("payload_mass", 0.0))
    if not stages_cfg:
        return {"traj": [], "final": {"h_m": req.alt0_m, "v_m_s": 0.0}}

    trajectory: list[dict[str, float | str]] = []
    altitude = req.alt0_m
    velocity = 0.0
    payload = payload_mass

    for stage_cfg in stages_cfg:
        best = _pick_best_rocket(int(stage_cfg.get("samples", 256)), int(stage_cfg.get("topk", 16)))
        isp = float(best.get("Isp_s", 0.0))
        thrust = float(best.get("F_N", 0.0))
        prop_mass = float(stage_cfg.get("prop_mass", 0.0))
        dry_mass = float(stage_cfg.get("dry_mass", 0.0))

        stage_mass = prop_mass + dry_mass + payload
        mdot = thrust / max(isp * G0, 1e-6)
        stage_time = 0.0
        prop_remaining = prop_mass

        while prop_remaining > 0.0:
            rho = _air_density(altitude)
            drag = 0.5 * rho * velocity * abs(velocity) * req.CdA
            acceleration = (thrust - drag - stage_mass * G0) / max(stage_mass, 1e-6)
            velocity += acceleration * req.dt_s
            altitude = max(0.0, altitude + velocity * req.dt_s)

            dm = min(mdot * req.dt_s, prop_remaining)
            stage_mass -= dm
            prop_remaining -= dm
            stage_time += req.dt_s

            if stage_time % 1.0 < req.dt_s:
                trajectory.append(
                    {
                        "stage": stage_cfg.get("name", "stage"),
                        "t": round(stage_time, 2),
                        "h_m": altitude,
                        "v_m_s": velocity,
                        "m_kg": stage_mass,
                        "D_N": drag,
                        "a_m_s2": acceleration,
                    }
                )

        payload = dry_mass + payload

    return {"traj": trajectory[-200:], "final": {"h_m": altitude, "v_m_s": velocity}}
 main
