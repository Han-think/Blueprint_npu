"""Runtime configuration helpers for Blueprint services."""

from __future__ import annotations

import os
from typing import Any, Dict


def get_config() -> Dict[str, Any]:
    """Return environment-driven configuration values.

    The helper is intentionally lightweight so individual FastAPI apps can
    consistently honour shared environment variables without duplicating the
    casting logic scattered across modules.
    """

    return {
        "BLUEPRINT_FAKE": os.getenv("BLUEPRINT_FAKE", "1"),
        "BLUEPRINT_DEVICE": os.getenv("BLUEPRINT_DEVICE", ""),
        "BLUEPRINT_TOPK": int(os.getenv("BLUEPRINT_TOPK", "16")),
        "BLUEPRINT_SAMPLES": int(os.getenv("BLUEPRINT_SAMPLES", "256")),
        "API_KEY": os.getenv("API_KEY", ""),
    }

