from __future__ import annotations

from typing import Iterable, Tuple


def _normal(a, b, c):
    import math

    ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
    nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
    norm = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
    return nx / norm, ny / norm, nz / norm


def write_ascii_stl(path: str, name: str, triangles: Iterable[Tuple[Tuple[float, float, float], Tuple[float, float, float], Tuple[float, float, float]]]):
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(f"solid {name}\n")
        for a, b, c in triangles:
            nx, ny, nz = _normal(a, b, c)
            handle.write(f"  facet normal {nx} {ny} {nz}\n")
            handle.write("    outer loop\n")
            handle.write(f"      vertex {a[0]} {a[1]} {a[2]}\n")
            handle.write(f"      vertex {b[0]} {b[1]} {b[2]}\n")
            handle.write(f"      vertex {c[0]} {c[1]} {c[2]}\n")
            handle.write("    endloop\n")
            handle.write("  endfacet\n")
        handle.write(f"endsolid {name}\n")
