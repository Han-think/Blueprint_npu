from __future__ import annotations

import math
from typing import List, Tuple


def annulus(r_in: float, r_out: float, length: float, seg: int = 64) -> List[Tuple[Tuple[float, float, float], Tuple[float, float, float], Tuple[float, float, float]]]:
    triangles = []

    def ring(x, radius):
        return [(x, radius * math.cos(2 * math.pi * j / seg), radius * math.sin(2 * math.pi * j / seg)) for j in range(seg)]

    r0_in, r0_out = r_in, r_out
    r1_in, r1_out = r_in * 0.98, r_out * 0.98
    a0_in, a0_out = ring(0.0, r0_in), ring(0.0, r0_out)
    a1_in, a1_out = ring(length, r1_in), ring(length, r1_out)

    for j in range(seg):
        a, b, c, d = a0_out[j], a1_out[j], a1_out[(j + 1) % seg], a0_out[(j + 1) % seg]
        triangles.append((a, b, c))
        triangles.append((a, c, d))
    for j in range(seg):
        a, b, c, d = a1_in[j], a0_in[j], a0_in[(j + 1) % seg], a1_in[(j + 1) % seg]
        triangles.append((a, b, c))
        triangles.append((a, c, d))
    return triangles
