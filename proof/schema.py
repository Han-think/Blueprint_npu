"""Reference schema metadata for proof-of-concept experiment logging."""

from __future__ import annotations

from typing import Dict

RUN_META: Dict[str, str] = {
    "run_id": "str",
    "mode": "base|rocket",
    "samples": "int",
    "topk": "int",
    "noise": "float",
    "seed": "int|None",
    "device": "str",
}

COMMON: Dict[str, str] = {
    "run_id": "str",
    "design_id": "int",
}

DESIGN: Dict[str, str] = {
    **COMMON,
    "design": "list|dict",
}

PREDICT: Dict[str, str] = {
    **COMMON,
    "pred": "dict",
}

MEASURE: Dict[str, str] = {
    **COMMON,
    "meas": "dict",
    "ts": "iso8601",
}
