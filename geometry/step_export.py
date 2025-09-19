"""STEP export helpers relying on pythonocc-core when available."""
from __future__ import annotations

from typing import List, Tuple
import math


def nozzle_profile(rt: float, eps: float, spike_deg: float, n: int = 100) -> List[Tuple[float, float]]:
    area_throat = math.pi * rt * rt
    re = math.sqrt(eps * area_throat / math.pi)
    tan_term = math.tan(math.radians(max(spike_deg, 1.0)))
    length = (re - rt) / max(tan_term, 1e-6)
    profile: List[Tuple[float, float]] = []
    for i in range(n + 1):
        x = length * i / n
        r = max(rt + (re - rt) * (i / n) ** 0.8, 1e-6)
        profile.append((x, r))
    return profile


def export_step_nozzle(path: str, rt: float, eps: float, spike_deg: float) -> str:
    try:
        from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeWire
        from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeRevol
        from OCC.Core.GeomAPI import GeomAPI_PointsToBSpline
        from OCC.Core.IFSelect import IFSelect_RetDone
        from OCC.Core.STEPControl import STEPControl_AsIs, STEPControl_Writer
        from OCC.Core.TColgp import TColgp_Array1OfPnt
        from OCC.Core.gp import gp_Ax2, gp_Dir, gp_Pnt
    except Exception as exc:  # pragma: no cover - optional dependency
        raise RuntimeError("pythonocc-core not available") from exc

    profile = nozzle_profile(rt, eps, spike_deg, n=80)
    points = TColgp_Array1OfPnt(1, len(profile))
    for idx, (x, r) in enumerate(profile, start=1):
        points.SetValue(idx, gp_Pnt(x, r, 0.0))
    spline = GeomAPI_PointsToBSpline(points).Curve()
    edge = BRepBuilderAPI_MakeEdge(spline).Edge()
    wire = BRepBuilderAPI_MakeWire(edge).Wire()
    axis = gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(1, 0, 0))
    solid = BRepPrimAPI_MakeRevol(wire, axis, 2 * math.pi).Shape()
    writer = STEPControl_Writer()
    writer.Transfer(solid, STEPControl_AsIs)
    status = writer.Write(path)
    if status != IFSelect_RetDone:
        raise RuntimeError("STEP write failed")
    return path
