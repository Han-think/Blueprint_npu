"""Helpers for emitting ASCII STL geometry."""

from __future__ import annotations

from typing import Iterable, Tuple


Triangle = Tuple[Tuple[float, float, float], Tuple[float, float, float], Tuple[float, float, float]]


def _normal(a: Tuple[float, float, float], b: Tuple[float, float, float], c: Tuple[float, float, float]) -> Tuple[float, float, float]:
    import math


    ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
    nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
    mag = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
    return nx / mag, ny / mag, nz / mag


def _emit_ascii(name: str, triangles: Iterable[Triangle]) -> str:
    lines = [f"solid {name}"]
    for a, b, c in triangles:
        nx, ny, nz = _normal(a, b, c)
        lines.append(f"  facet normal {nx} {ny} {nz}")
        lines.append("    outer loop")
        lines.append(f"      vertex {a[0]} {a[1]} {a[2]}")
        lines.append(f"      vertex {b[0]} {b[1]} {b[2]}")
        lines.append(f"      vertex {c[0]} {c[1]} {c[2]}")
        lines.append("    endloop")
        lines.append("  endfacet")
    lines.append(f"endsolid {name}")
    return "\n".join(lines) + "\n"


def write_ascii_stl(path: str, name: str, triangles: Iterable[Triangle]) -> None:
    """Write triangles to ``path`` as an ASCII STL file."""

    with open(path, "w", encoding="utf-8") as handle:
        handle.write(_emit_ascii(name, triangles))


def ascii_stl_bytes(name: str, triangles: Iterable[Triangle]) -> bytes:
    """Return the ASCII STL payload for the provided triangles."""

    return _emit_ascii(name, triangles).encode("utf-8")


__all__ = ["ascii_stl_bytes", "write_ascii_stl"]
