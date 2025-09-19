from __future__ import annotations

import math
from typing import Optional
import math
from typing import Optional

from fastapi import Depends, FastAPI
from pydantic import BaseModel

from app.security import require_api_key
from assembly.builder import _pick_best_rocket
from assembly.presets import PRESETS

G0 = 9.80665


def air_density(alt: float):
    if alt < 11_000.0:
        T = 288.15 - 0.0065 * alt
        P = 101_325.0 * (T / 288.15) ** (-5.25588)
    else:
        T = 216.65
        P = 22_632.06 * math.exp(-G0 * (alt - 11_000) / (287.0 * T))
    rho = P / (287.0 * T)
    return rho


class AscentRequest(BaseModel):
    preset: Optional[str] = "rocket_3stage_demo"
    CdA: float = 2.0
    dt_s: float = 0.1
    alt0_m: float = 0.0


app = FastAPI(title="Ascent API")


@app.get("/ascent/health")
def health():
    return {"status": "ok"}


@app.post("/ascent/rocket")
def rocket(req: AscentRequest, _: None = Depends(require_api_key)):
    cfg = PRESETS[req.preset]["rocket"]
    stages = cfg["stages"]
    payload = cfg["payload_mass"]
    trajectory = []
    velocity = 0.0
    altitude = req.alt0_m
    payload_mass = payload

    for stage in stages:
        best = _pick_best_rocket(samples=int(stage["samples"]), topk=int(stage["topk"]))
        isp = float(best["Isp_s"])
        thrust = float(best["F_N"])
        prop_mass = float(stage["prop_mass"])
        dry_mass = float(stage["dry_mass"])
        mass = prop_mass + dry_mass + payload_mass
        mdot = thrust / (isp * G0)
        time_elapsed = 0.0
        prop_remaining = prop_mass
        while prop_remaining > 0:
            rho = air_density(altitude)
            drag = 0.5 * rho * velocity * abs(velocity) * req.CdA
            acceleration = (thrust - drag - mass * G0) / max(mass, 1e-6)
            velocity += acceleration * req.dt_s
            altitude = max(0.0, altitude + velocity * req.dt_s)
            dm = min(mdot * req.dt_s, prop_remaining)
            mass -= dm
            prop_remaining -= dm
            time_elapsed += req.dt_s
            if time_elapsed % 1.0 < req.dt_s:
                trajectory.append(
                    {
                        "stage": stage["name"],
                        "t": round(time_elapsed, 2),
                        "h_m": altitude,
                        "v_m_s": velocity,
                        "m_kg": mass,
                        "D_N": drag,
                        "a_m_s2": acceleration,
                    }
                )
        payload_mass = dry_mass + payload_mass
    return {"traj": trajectory[-200:], "final": {"h_m": altitude, "v_m_s": velocity}}
