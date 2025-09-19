 codex/initialize-npu-inference-template-v1n7c2
from __future__ import annotations

from typing import List

from fastapi import Depends, FastAPI
from pydantic import BaseModel

from app.security import require_api_key

app = FastAPI(title="Mission API")


class MissionLeg(BaseModel):
    type: str
    duration_s: float


class MissionRequest(BaseModel):
    legs: List[MissionLeg]

"""Mission analysis API providing simple fighter leg summaries."""

from __future__ import annotations

import math
from typing import List

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.security import require_api_key

R_AIR = 287.0
GAMMA = 1.4
G0 = 9.80665


def _isa(altitude_m: float) -> tuple[float, float, float, float]:
    """Return (T, P, rho, a) for a simple ISA approximation."""

    if altitude_m < 11_000.0:
        temperature = 288.15 - 0.0065 * altitude_m
        pressure = 101_325.0 * (temperature / 288.15) ** (GAMMA * R_AIR / (-0.0065 * R_AIR))
    else:
        temperature = 216.65
        p_11 = 22_632.06
        pressure = p_11 * math.exp(-G0 * (altitude_m - 11_000.0) / (R_AIR * temperature))
    density = pressure / (R_AIR * temperature)
    sound_speed = math.sqrt(GAMMA * R_AIR * temperature)
    return temperature, pressure, density, sound_speed


class Leg(BaseModel):
    """Mission leg describing Mach target and duration."""

    type: str = Field(..., description="accel|cruise|dash|loiter")
    M: float
    dt_s: float


class MissionReq(BaseModel):
    """Mission request body."""

    M0: float = 0.9
    alt_m: float = 2_000.0
    legs: List[Leg]
    airframe_mass_kg: float = 11_000.0
    fuel_kg: float = 3_000.0
    CdA: float = 1.2


app = FastAPI(title="Mission API")
 main


@app.get("/mission/health")
def health() -> dict[str, str]:
 codex/initialize-npu-inference-template-v1n7c2
    return {"status": "ok"}


@app.post("/mission/run")
def run_mission(req: MissionRequest, _: None = Depends(require_api_key)) -> dict[str, int]:
    return {"legs": len(req.legs)}

    """Return readiness state."""

    return {"status": "ok"}


@app.post("/mission/fighter")
def fighter(req: MissionReq, _: None = Depends(require_api_key)) -> dict[str, object]:
    """Estimate fuel usage over the requested mission profile."""

    from importlib import import_module

    pipeline_module = import_module("pencil.pipeline")
    PencilPipeline = getattr(pipeline_module, "PencilPipeline")

    pipeline = PencilPipeline()
    candidates = pipeline.optimize(samples=256, topk=8, M0=req.M0, alt_m=req.alt_m)
    if not candidates:
        raise HTTPException(status_code=503, detail="pencil pipeline unavailable")
    best = candidates[0]
    tsfc = float(best["TSFC_kg_per_Ns"])

    legs: List[dict[str, object]] = []
    mass_airframe = req.airframe_mass_kg
    fuel_remaining = req.fuel_kg

    for leg in req.legs:
        _temperature, _pressure, density, sound_speed = _isa(req.alt_m)
        velocity = leg.M * sound_speed
        drag = 0.5 * density * velocity * velocity * req.CdA
        required_thrust = max(drag + 0.05 * (mass_airframe + fuel_remaining) * G0, 0.0)
        fuel_used = tsfc * required_thrust * leg.dt_s
        fuel_used = min(fuel_used, fuel_remaining)
        fuel_remaining -= fuel_used
        legs.append(
            {
                "type": leg.type,
                "M": leg.M,
                "dt_s": leg.dt_s,
                "V_m_s": velocity,
                "F_req_N": required_thrust,
                "fuel_used_kg": fuel_used,
                "fuel_left_kg": fuel_remaining,
            }
        )

    summary = {
        "engine": {
            "F_N": float(best["F_N"]),
            "TSFC_kg_per_Ns": tsfc,
            "spec_thrust": float(best["spec_thrust_N_per_kgps"]),
        },
        "airframe": {"mass_kg": mass_airframe},
        "fuel_final_kg": fuel_remaining,
    }
    return {"legs": legs, "summary": summary}
 main
