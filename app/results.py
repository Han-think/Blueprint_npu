from fastapi import FastAPI, Response, HTTPException
from pathlib import Path
import json
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
    items = sorted([p.name for p in PARETO_DIR.glob("*.json")])
    return {"files": items, "count": len(items)}


@app.get("/results/get")
def get_result(name: str):
    p = PARETO_DIR / name
    if not p.is_file():
        raise HTTPException(404, f"not found: {name}")
    return json.loads(p.read_text(encoding="utf-8"))


@app.get("/results/topstl")
def top_stl(name: str, index: int = 0, seg: int = 96):
    p = PARETO_DIR / name
    if not p.is_file():
        raise HTTPException(404, f"not found: {name}")
    data = json.loads(p.read_text(encoding="utf-8"))
    items = data.get("top", [])
    if not items:
        raise HTTPException(400, "empty top list")
    i = max(0, min(index, len(items) - 1))
    d = items[i].get("design") or {}
    rt_mm = float(d.get("rt_mm", 20.0))
    eps = float(d.get("eps", 20.0))
    spike_deg = float(d.get("spike_deg", 10.0))
    prof = nozzle_profile(rt_mm * 1e-3, eps, spike_deg, n=120)
    tris = revolve_to_triangles(prof, seg=seg)
    path = f"data/geometry/{name.replace('.json', '')}_top{i}.stl"
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    write_ascii_stl(path, "nozzle_top", tris)
    data_bin = Path(path).read_bytes()
    return Response(content=data_bin, media_type="model/stl")
