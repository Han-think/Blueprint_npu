from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_DEFAULT: dict[str, Any] = {
    "design_space": [
        {"name": "x0", "low": -1.0, "high": 1.0},
        {"name": "x1", "low": -1.0, "high": 1.0},
        {"name": "x2", "low": -1.0, "high": 1.0},
    ],
    "constraints": {"max_abs": 0.9, "sum_limit": 2.0},
}


def load_config() -> dict[str, Any]:
    path = Path("data/design_space.yaml")
    if path.is_file():
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            return loaded
    return _DEFAULT
