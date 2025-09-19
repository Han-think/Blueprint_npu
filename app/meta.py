from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI

app = FastAPI(title="Meta API")


def _read_json(path: str, default):
    file_path = Path(path)
    if file_path.is_file():
        try:
            return json.loads(file_path.read_text(encoding="utf-8"))
        except Exception:  # pragma: no cover - defensive
            return default
    return default


@app.get("/meta/health")
def health():
    return {"status": "ok"}


@app.get("/meta/units")
def units():
    return _read_json("data/schema_units.json", {"version": "none"})


@app.get("/meta/catalog")
def catalog():
    from catalog.rocket_wrap import ROCKET_TYPES
    from catalog.pencil_wrap import PENCIL_TYPES

    return {"rocket": list(ROCKET_TYPES.keys()), "pencil": list(PENCIL_TYPES.keys())}


@app.get("/meta/manufacturing")
def manufacturing():
    return _read_json("manufacturing/rules.json", {"version": "none"})
