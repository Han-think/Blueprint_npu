"""FastAPI entry point that assembles rocket and pencil demo configurations."""

from __future__ import annotations

import copy
from typing import Any, Dict, Optional

from fastapi import FastAPI
from pydantic import BaseModel

from assembly.builder import build_hybrid_summary, build_pencil_assembly, build_rocket_assembly
from assembly.presets import PRESETS

app = FastAPI(title="Assembly API")


class BuildReq(BaseModel):
    """Request payload for the assembly build endpoint."""

    preset: Optional[str] = None
    rocket: Optional[Dict[str, Any]] = None
    pencil: Optional[Dict[str, Any]] = None


@app.get("/assembly/health")
def health() -> Dict[str, Any]:
    """Report readiness of the assembly service."""

    return {"status": "ok", "modes": ["rocket_assembly", "pencil_assembly", "hybrid_summary"]}


@app.get("/assembly/presets")
def presets() -> Dict[str, Any]:
    """Expose the canonical presets for discovery."""

    return {"keys": list(PRESETS.keys()), "examples": PRESETS}


@app.post("/assembly/build")
def build(req: BuildReq) -> Dict[str, Any]:
    """Assemble rocket and pencil subsystems using presets or custom overrides."""

    preset_cfg = PRESETS.get(req.preset or "") or {}

    rocket_cfg: Optional[Dict[str, Any]] = None
    if "rocket" in preset_cfg:
        rocket_cfg = copy.deepcopy(preset_cfg["rocket"])
    if req.rocket is not None:
        rocket_cfg = {**(rocket_cfg or {}), **req.rocket}

    pencil_cfg: Optional[Dict[str, Any]] = None
    if "pencil" in preset_cfg:
        pencil_cfg = copy.deepcopy(preset_cfg["pencil"])
    if req.pencil is not None:
        pencil_cfg = {**(pencil_cfg or {}), **req.pencil}

    rocket_result = build_rocket_assembly(rocket_cfg)
    pencil_result = build_pencil_assembly(pencil_cfg)
    hybrid = build_hybrid_summary(rocket_result, pencil_result)

    return {"rocket": rocket_result, "pencil": pencil_result, "hybrid": hybrid}


__all__ = ["app", "build", "health", "presets", "BuildReq"]
