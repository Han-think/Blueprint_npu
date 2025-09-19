from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI

app = FastAPI(title="Materials API")
MATERIALS_PATH = Path("data/materials/rocket_alloys.json")


def _load():
    if MATERIALS_PATH.is_file():
        return json.loads(MATERIALS_PATH.read_text(encoding="utf-8"))
    return {"materials": {}}


@app.get("/materials/health")
def health():
    return {"status": "ok"}


@app.get("/materials/list")
def list_materials():
    data = _load()
    return {"keys": list(data.get("materials", {}).keys())}


@app.get("/materials/get")
def get_material(name: str):
    data = _load()
    material = data.get("materials", {}).get(name)
    return material or {}
