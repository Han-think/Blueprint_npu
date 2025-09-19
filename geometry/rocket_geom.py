from __future__ import annotations

import math
from typing import List, Tuple


def nozzle_profile(rt: float, eps: float, spike_deg: float, n: int = 100) -> List[Tuple[float, float]]:
    At = math.pi * rt * rt
    re = math.sqrt(eps * At / math.pi)
    length = (re - rt) / math.tan(math.radians(max(spike_deg, 1.0)))
    profile = []
    for i in range(n + 1):
        x = length * i / n
        radius = max(rt + (re - rt) * (i / n) ** 0.8, 1e-6)
        profile.append((x, radius))
    profile.insert(0, (0.0, rt))
    return profile


def revolve_to_triangles(profile: List[Tuple[float, float]], seg: int = 64):
    triangles = []
    for i in range(len(profile) - 1):
        x0, r0 = profile[i]
        x1, r1 = profile[i + 1]
        for j in range(seg):
            theta0 = 2 * math.pi * j / seg
            theta1 = 2 * math.pi * (j + 1) / seg
            a = (x0, r0 * math.cos(theta0), r0 * math.sin(theta0))
            b = (x1, r1 * math.cos(theta0), r1 * math.sin(theta0))
            c = (x1, r1 * math.cos(theta1), r1 * math.sin(theta1))
            d = (x0, r0 * math.cos(theta1), r0 * math.sin(theta1))
            triangles.append((a, b, c))
            triangles.append((a, c, d))
    return triangles
