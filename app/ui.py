from __future__ import annotations

import hashlib
import subprocess
import sys
import time
from pathlib import Path
from typing import List

from fastapi import FastAPI, Query
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
)

BASE = Path(".").resolve()
GEO = BASE / "data" / "geometry"
PAR = BASE / "data" / "pareto"
UI = BASE / "app" / "ui_static"

app = FastAPI(title="Blueprint UI")


@app.get("/ui/health")
def health() -> dict[str, object]:
    return {"ok": True, "geometry": GEO.exists(), "pareto": PAR.exists()}


@app.get("/ui")
def index() -> HTMLResponse:
    html = (UI / "index.html").read_text(encoding="utf-8")
    return HTMLResponse(html)


@app.get("/ui/list")
def list_files() -> dict[str, List[dict[str, object]]]:
    out: dict[str, List[dict[str, object]]] = {"stl": [], "pareto": []}
    if GEO.exists():
        for path in sorted(GEO.glob("*.stl")):
            out["stl"].append({"name": path.name, "bytes": path.stat().st_size})
    if PAR.exists():
        for path in sorted(PAR.glob("*.json")):
            out["pareto"].append({"name": path.name, "bytes": path.stat().st_size})
    return out


@app.get("/ui/file")
def get_file(
    path: str = Query(
        ..., description="data/geometry/*.stl 또는 data/pareto/*.json"
    )
):
    target = (BASE / path).resolve()
    if not target.is_file() or BASE not in target.parents:
        return PlainTextResponse("not found", status_code=404)
    if target.suffix.lower() == ".stl":
        return FileResponse(target, media_type="model/stl")
    if target.suffix.lower() == ".json":
        return FileResponse(target, media_type="application/json")
    return PlainTextResponse("unsupported", status_code=415)


@app.post("/ui/generate")
def generate():
    t0 = time.time()
    try:
        subprocess.run([sys.executable, "scripts/ci_make_artifacts.py"], check=True)
    except Exception as exc:  # pragma: no cover - bubble up message
        return JSONResponse({"ok": False, "error": str(exc)})
    elapsed = round(time.time() - t0, 2)
    return {"ok": True, "t_sec": elapsed}


@app.get("/ui/manifest")
def manifest() -> dict[str, List[dict[str, object]]]:
    man: dict[str, List[dict[str, object]]] = {"stl": [], "pareto": []}
    for path in sorted(GEO.glob("*.stl")):
        data = path.read_bytes()
        man["stl"].append(
            {
                "name": path.name,
                "size": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )
    for path in sorted(PAR.glob("*.json")):
        data = path.read_bytes()
        man["pareto"].append(
            {
                "name": path.name,
                "size": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )
    return man
