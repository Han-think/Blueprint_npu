"""Crude annular duct geometry for pencil engine demos."""

from __future__ import annotations

import math

from typing import List, Tuple


Triangle = Tuple[Tuple[float, float, float], Tuple[float, float, float], Tuple[float, float, float]]


def _ring(x: float, radius: float, seg: int) -> List[Tuple[float, float, float]]:
    return [
        (x, radius * math.cos(2.0 * math.pi * j / seg), radius * math.sin(2.0 * math.pi * j / seg))
        for j in range(seg)
    ]


def annulus(r_in: float, r_out: float, length: float, seg: int = 64) -> List[Triangle]:
    """Generate an annular duct between ``r_in`` and ``r_out``."""

    seg = max(seg, 3)
    r0_in, r0_out = r_in, r_out
    r1_in, r1_out = r_in * 0.98, r_out * 0.98

    A0_in, A0_out = _ring(0.0, r0_in, seg), _ring(0.0, r0_out, seg)
    A1_in, A1_out = _ring(length, r1_in, seg), _ring(length, r1_out, seg)

    triangles: List[Triangle] = []

    for j in range(seg):
        a, b, c, d = A0_out[j], A1_out[j], A1_out[(j + 1) % seg], A0_out[(j + 1) % seg]
        triangles.extend([(a, b, c), (a, c, d)])

    for j in range(seg):
        a, b, c, d = A1_in[j], A0_in[j], A0_in[(j + 1) % seg], A1_in[(j + 1) % seg]
        triangles.extend([(a, b, c), (a, c, d)])

    return triangles


__all__ = ["annulus"]
