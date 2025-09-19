"""FastAPI app exposing lightweight geometry utilities."""

from __future__ import annotations

from fastapi import FastAPI, Response

from geometry.export_stl import ascii_stl_bytes
from geometry.pencil_geom import annulus
from geometry.rocket_geom import nozzle_profile, revolve_to_triangles

app = FastAPI(title="Geometry API")


@app.get("/geom/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/geom/rocket/nozzle")
def rocket_nozzle(
    rt_mm: float,
    eps: float,
    spike_deg: float,
    seg: int = 64,
    n: int = 100,
    as_stl: int = 0,
):
    rt = rt_mm * 1e-3
    profile = nozzle_profile(rt, eps, spike_deg, n=n)

    if as_stl:
        triangles = revolve_to_triangles(profile, seg=seg)
        payload = ascii_stl_bytes("nozzle", triangles)
        return Response(content=payload, media_type="model/stl")

    return {"profile": profile, "count": len(profile)}


@app.get("/geom/pencil/duct")
def pencil_duct(
    r_in_mm: float = 200.0,
    r_out_mm: float = 350.0,
    length_mm: float = 800.0,
    seg: int = 64,
    as_stl: int = 0,
):
    triangles = annulus(r_in_mm * 1e-3, r_out_mm * 1e-3, length_mm * 1e-3, seg=seg)

    if as_stl:
        payload = ascii_stl_bytes("duct", triangles)
        return Response(content=payload, media_type="model/stl")

    return {"triangles": len(triangles)}


__all__ = ["app"]
