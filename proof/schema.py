from __future__ import annotations

RUN_META = {
    "run_id": "str",
    "mode": "base|rocket",
    "samples": "int",
    "topk": "int",
    "noise": "float",
    "seed": "int|None",
    "device": "str",
}

COMMON = {"run_id": "str", "design_id": "int"}

DESIGN = {**COMMON, "design": "list|dict"}

PREDICT = {**COMMON, "pred": "dict"}

MEASURE = {**COMMON, "meas": "dict", "ts": "iso8601"}
