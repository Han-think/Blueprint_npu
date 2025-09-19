"""FastAPI service exposing rocket material reference data."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException

DATA_PATH = Path("data/materials/rocket_alloys.json")

app = FastAPI(title="Materials API")


def _load() -> dict:
    if not DATA_PATH.is_file():
        raise HTTPException(status_code=404, detail="materials file missing")
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


@app.get("/materials/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/materials/list")
def list_materials() -> dict:
    data = _load()
    return {"keys": sorted(data.get("materials", {}).keys())}


@app.get("/materials/get")
def get_material(name: str) -> dict:
    data = _load()
    mat = data.get("materials", {}).get(name)
    if mat is None:
        raise HTTPException(status_code=404, detail=f"material not found: {name}")
    return mat
