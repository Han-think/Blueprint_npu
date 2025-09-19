from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import FastAPI
from pydantic import BaseModel

from assembly.builder import build_hybrid_summary, build_pencil_assembly, build_rocket_assembly
from assembly.presets import PRESETS

app = FastAPI(title="Assembly API")


class BuildRequest(BaseModel):
    preset: Optional[str] = None
    rocket: Optional[Dict[str, Any]] = None
    pencil: Optional[Dict[str, Any]] = None


@app.get("/assembly/health")
def health():
    return {"status": "ok", "modes": ["rocket_assembly", "pencil_assembly", "hybrid_summary"]}


@app.get("/assembly/presets")
def presets():
    return {"keys": list(PRESETS.keys()), "examples": PRESETS}


@app.post("/assembly/build")
def build(req: BuildRequest):
    cfg = PRESETS.get(req.preset, {})
    rocket_cfg = req.rocket or cfg.get("rocket")
    pencil_cfg = req.pencil or cfg.get("pencil")
    rocket_res = build_rocket_assembly(rocket_cfg) if rocket_cfg else None
    pencil_res = build_pencil_assembly(pencil_cfg) if pencil_cfg else None
    hybrid = build_hybrid_summary(rocket_res, pencil_res)
    return {"rocket": rocket_res, "pencil": pencil_res, "hybrid": hybrid}
