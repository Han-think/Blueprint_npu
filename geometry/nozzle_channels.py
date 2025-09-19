"""Helpers for generating nozzle wall thickness and channel meshes."""

from __future__ import annotations

import math

from typing import List, Tuple

Vec2 = Tuple[float, float]
Vec3 = Tuple[float, float, float]
Triangle = Tuple[Vec3, Vec3, Vec3]


def _polygon_circle(radius: float, segments: int) -> List[Vec2]:
    return [
        (radius * math.cos(2.0 * math.pi * j / segments), radius * math.sin(2.0 * math.pi * j / segments))
        for j in range(segments)
    ]


def _extrude_ring(x0: float, x1: float, inner_r: float, outer_r: float, segments: int = 64) -> List[Triangle]:
    tris: List[Triangle] = []
    inner0 = _polygon_circle(inner_r, segments)
    outer0 = _polygon_circle(outer_r, segments)
    inner0_3d = [(x0, x, y) for x, y in inner0]
    outer0_3d = [(x0, x, y) for x, y in outer0]
    inner1_3d = [(x1, x, y) for x, y in inner0]
    outer1_3d = [(x1, x, y) for x, y in outer0]

    for idx in range(segments):
        nxt = (idx + 1) % segments
        # outer wall
        a, b, c, d = outer0_3d[idx], outer1_3d[idx], outer1_3d[nxt], outer0_3d[nxt]
        tris.extend([(a, b, c), (a, c, d)])
        # inner wall
        a, b, c, d = inner1_3d[idx], inner0_3d[idx], inner0_3d[nxt], inner1_3d[nxt]
        tris.extend([(a, b, c), (a, c, d)])
    return tris


def straight_channels(
    x0: float,
    x1: float,
    radius_mid: float,
    thickness: float,
    channel_count: int,
    segments: int = 64,
) -> List[Triangle]:
    """Generate straight cooling channels as thin extruded rings."""

    tris: List[Triangle] = []
    for _ in range(channel_count):
        radial_inner = radius_mid - 0.5 * thickness
        radial_outer = radius_mid + 0.5 * thickness
        tris.extend(_extrude_ring(x0, x1, radial_inner, radial_outer, segments=segments))
    return tris
