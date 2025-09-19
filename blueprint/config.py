from __future__ import annotations
 codex/initialize-npu-inference-template-v1n7c2

from pathlib import Path
from typing import Any, Dict

import yaml

_DEFAULT_CONFIG: Dict[str, Any] = {
    "design_space": [
        {"name": "x0", "low": -1.0, "high": 1.0},
        {"name": "x1", "low": -1.0, "high": 1.0},
        {"name": "x2", "low": -1.0, "high": 1.0},
    ],
    "constraints": {"max_abs": 0.9, "sum_limit": 2.0},
}


def load_config() -> Dict[str, Any]:
    path = Path("data/design_space.yaml")
    if path.is_file():
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    return _DEFAULT_CONFIG.copy()

import yaml
from pathlib import Path

_DEFAULT = {
    "design_space": [
        {"name": "x0", "low": -1.0, "high": 1.0},
        {"name": "x1", "low": -1.0, "high": 1.0},
        {"name": "x2", "low": -1.0, "high": 1.0}
    ],
    "constraints": {"max_abs": 0.9, "sum_limit": 2.0}
}

def load_config():
    p = Path("data/design_space.yaml")
    if p.is_file():
        return yaml.safe_load(p.read_text(encoding="utf-8"))
    return _DEFAULT
 main
