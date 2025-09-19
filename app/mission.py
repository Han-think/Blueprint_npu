from __future__ import annotations

import math
from typing import List, Optional

from fastapi import Depends, FastAPI
import math
from typing import List

from fastapi import Depends, FastAPI
from pydantic import BaseModel, Field

from app.security import require_api_key
from pencil.pipeline import PencilPipeline

G0 = 9.80665
R = 287.0
GAM = 1.4


def isa(alt: float):
    if alt < 11_000.0:
        T = 288.15 - 0.0065 * alt
        P = 101_325.0 * (T / 288.15) ** (GAM * R / (-0.0065 * R))
    else:
        T = 216.65
        base = 22632.06
        P = base * math.exp(-G0 * (alt - 11_000.0) / (R * T))
    rho = P / (R * T)
    a = math.sqrt(GAM * R * T)
    return T, P, rho, a


class Leg(BaseModel):
    type: str = Field(..., description="accel|cruise|dash|loiter")
    M: float
    dt_s: float


class MissionRequest(BaseModel):
    M0: float = 0.9
    alt_m: float = 2000.0
    legs: List[Leg]
    airframe_mass_kg: float = 11_000.0
    fuel_kg: float = 3_000.0
    CdA: float = 1.2


app = FastAPI(title="Mission API")


@app.get("/mission/health")
def health():
    return {"status": "ok"}


@app.post("/mission/fighter")
def fighter(req: MissionRequest, _: None = Depends(require_api_key)):
    pipeline = PencilPipeline()
    top = pipeline.optimize(samples=256, topk=8, M0=req.M0, alt_m=req.alt_m)[0]
    tsfc = float(top["TSFC_kg_per_Ns"])
    summary = {
        "engine": {
            "F_N": float(top["F_N"]),
            "TSFC_kg_per_Ns": tsfc,
            "spec_thrust": float(top["spec_thrust_N_per_kgps"]),
        },
        "airframe": {"mass_kg": req.airframe_mass_kg},
        "fuel_final_kg": req.fuel_kg,
    }
    legs_out = []
    fuel_remaining = req.fuel_kg
    for leg in req.legs:
        T, P, rho, a = isa(req.alt_m)
        velocity = leg.M * a
        drag = 0.5 * rho * velocity * velocity * req.CdA
        thrust_required = max(drag + 0.05 * (req.airframe_mass_kg + fuel_remaining) * G0, 0.0)
        fuel_used = tsfc * thrust_required * leg.dt_s
        fuel_used = min(fuel_used, fuel_remaining)
        fuel_remaining -= fuel_used
        legs_out.append(
            {
                "type": leg.type,
                "M": leg.M,
                "dt_s": leg.dt_s,
                "V_m_s": velocity,
                "F_req_N": thrust_required,
                "fuel_used_kg": fuel_used,
                "fuel_left_kg": fuel_remaining,
            }
        )
    summary["fuel_final_kg"] = fuel_remaining
    return {"legs": legs_out, "summary": summary}
