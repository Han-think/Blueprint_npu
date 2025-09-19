 codex/initialize-npu-inference-template-v1n7c2
from __future__ import annotations

from fastapi import FastAPI

"""Extended geometry API providing channelized nozzle export."""

from __future__ import annotations

from fastapi import FastAPI, Response

from geometry.export_stl import write_ascii_stl
from geometry.nozzle_channels import straight_channels
from geometry.rocket_geom import nozzle_profile, revolve_to_triangles
 main

app = FastAPI(title="Geometry2 API")


 codex/initialize-npu-inference-template-v1n7c2
@app.get("/geometry2/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

@app.get("/geom2/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/geom2/rocket/nozzle_channels")
def nozzle_channels(
    rt_mm: float,
    eps: float,
    spike_deg: float,
    t_mm: float = 2.0,
    n_ch: int = 24,
    L_scale: float = 1.0,
    seg: int = 64,
) -> Response:
    rt = rt_mm * 1e-3
    profile = nozzle_profile(rt, eps, spike_deg, n=50)
    length = profile[-1][0] * L_scale
    triangles = revolve_to_triangles(profile, seg=seg)
    triangles += straight_channels(0.0, length, radius_mid=rt * 1.4, thickness=t_mm * 1e-3, channel_count=n_ch, segments=seg)
    path = "nozzle_channels.stl"
    write_ascii_stl(path, "nozzle_channels", triangles)
    data = open(path, "rb").read()
    return Response(content=data, media_type="model/stl")
 main
