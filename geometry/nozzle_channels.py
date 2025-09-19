from __future__ import annotations

import math
from typing import List, Tuple


def polygon_circle(radius: float, seg: int):
    return [(radius * math.cos(2 * math.pi * j / seg), radius * math.sin(2 * math.pi * j / seg)) for j in range(seg)]


def extrude_ring(x0: float, x1: float, r_in: float, r_out: float, seg: int = 64):
    triangles = []
    inner0 = polygon_circle(r_in, seg)
    outer0 = polygon_circle(r_out, seg)
    inner1 = [(x1, x, y) for x, y in inner0]
    outer1 = [(x1, x, y) for x, y in outer0]
    inner0 = [(x0, x, y) for x, y in inner0]
    outer0 = [(x0, x, y) for x, y in outer0]
    for j in range(seg):
        a, b, c, d = outer0[j], outer1[j], outer1[(j + 1) % seg], outer0[(j + 1) % seg]
        triangles.append((a, b, c))
        triangles.append((a, c, d))
        a, b, c, d = inner1[j], inner0[j], inner0[(j + 1) % seg], inner1[(j + 1) % seg]
        triangles.append((a, b, c))
        triangles.append((a, c, d))
    return triangles


def straight_channels(x0: float, x1: float, r_mid: float, thickness: float, n_ch: int, seg: int = 64):
    triangles = []
    for k in range(n_ch):
        angle = 2 * math.pi * k / n_ch
        r1 = r_mid - 0.5 * thickness
        r2 = r_mid + 0.5 * thickness
        triangles.extend(extrude_ring(x0, x1, r1, r2, seg=seg))
    return triangles
