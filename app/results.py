from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException, Response

from geometry.rocket_geom import nozzle_profile, revolve_to_triangles
from geometry.export_stl import write_ascii_stl

app = FastAPI(title="Results API")
PARETO_DIR = Path("data/pareto")


@app.get("/results/health")
def health():
    return {"status": "ok"}


@app.get("/results/list")
def list_results():
    PARETO_DIR.mkdir(parents=True, exist_ok=True)
    items = sorted(p.name for p in PARETO_DIR.glob("*.json"))
    return {"files": items, "count": len(items)}


@app.get("/results/get")
def get_result(name: str):
    path = PARETO_DIR / name
    if not path.is_file():
        raise HTTPException(404, f"not found: {name}")
    return json.loads(path.read_text(encoding="utf-8"))


@app.get("/results/topstl")
def top_stl(name: str, index: int = 0, seg: int = 96):
    path = PARETO_DIR / name
    if not path.is_file():
        raise HTTPException(404, f"not found: {name}")
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data.get("top", [])
    if not items:
        raise HTTPException(400, "empty top list")
    idx = max(0, min(index, len(items) - 1))
    design = items[idx].get("design") or {}
    rt_mm = float(design.get("rt_mm", 20.0))
    eps = float(design.get("eps", 20.0))
    spike_deg = float(design.get("spike_deg", 10.0))
    profile = nozzle_profile(rt_mm * 1e-3, eps, spike_deg, n=120)
    triangles = revolve_to_triangles(profile, seg=seg)
    out_path = Path("data/geometry") / f"{path.stem}_top{idx}.stl"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_ascii_stl(str(out_path), "nozzle_top", triangles)
    data_bin = out_path.read_bytes()
    return Response(content=data_bin, media_type="model/stl")
