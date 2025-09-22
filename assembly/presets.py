"""Preset configurations for assembling rocket and pencil demo stacks."""

from __future__ import annotations

from typing import Any, Dict

PRESETS: Dict[str, Dict[str, Any]] = {
    "rocket_3stage_demo": {
        "rocket": {
            "payload_mass": 2000.0,
            "stages": [
                {"name": "S1", "samples": 256, "topk": 8, "prop_mass": 120_000.0, "dry_mass": 10_000.0},
                {"name": "S2", "samples": 256, "topk": 8, "prop_mass": 30_000.0, "dry_mass": 3_000.0},
                {"name": "S3", "samples": 256, "topk": 8, "prop_mass": 6_000.0, "dry_mass": 800.0},
            ],
        }
    },
    "pencil_fighter_demo": {
        "pencil": {
            "samples": 256,
            "topk": 8,
            "M0": 0.9,
            "alt_m": 2000.0,
            "airframe": {"mass_kg": 11_000.0, "fuel_kg": 3_200.0},
            "ramjet_boost": {"enable": True, "M_on": 1.8, "gain_pct": 18.0},
        }
    },
    "hybrid_full_demo": {
        "rocket": {
            "payload_mass": 1500.0,
            "stages": [
                {"name": "S1", "samples": 128, "topk": 4, "prop_mass": 90_000.0, "dry_mass": 8_000.0},
                {"name": "S2", "samples": 128, "topk": 4, "prop_mass": 25_000.0, "dry_mass": 2_500.0},
                {"name": "S3", "samples": 128, "topk": 4, "prop_mass": 5_000.0, "dry_mass": 700.0},
            ],
        },
        "pencil": {
            "samples": 128,
            "topk": 4,
            "M0": 0.85,
            "alt_m": 1500.0,
            "airframe": {"mass_kg": 10_000.0, "fuel_kg": 2_800.0},
            "ramjet_boost": {"enable": True, "M_on": 1.6, "gain_pct": 12.0},
        },
    },
}
"""Canonical presets shipped with the assembly extension."""

__all__ = ["PRESETS"]
