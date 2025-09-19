"""Lightweight data-acquisition stub for demo purposes."""

from __future__ import annotations

import datetime as dt
import random
from typing import Dict


def read_measurement(pred: Dict[str, float], noise: float = 0.03) -> Dict[str, float]:
    """Return a noisy measurement dictionary with a timestamp."""

    meas: Dict[str, float] = {}
    for key, value in pred.items():
        if not isinstance(value, (int, float)):
            continue
        mu = float(value)
        sigma = abs(mu) * noise
        meas[key] = mu + random.gauss(0.0, sigma) - 0.005 * mu
    meas["ts"] = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    return meas


__all__ = ["read_measurement"]
