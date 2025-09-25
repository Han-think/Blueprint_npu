from __future__ import annotations
from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse
from pathlib import Path
from datetime import datetime
import math, json

api = APIRouter(prefix="/wb", tags=["saturn"])
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT/"data"
RUNS = DATA/"geometry/cad/saturn_cad_runs"
RUNS.mkdir(parents=True, exist_ok=True)

def _tri_flat(v): return " ".join(f"{a:.6f}" for a in v)
def write_ascii_stl(path:Path, verts, faces, name="part"):
    with path.open("w", encoding="utf-8") as f:
        f.write(f"solid {name}\n")
        for (i,j,k) in faces:
            a,b,c = verts[i], verts[j], verts[k]
            # 평면 법선(대충)
            ux,uy,uz = (b[0]-a[0], b[1]-a[1], b[2]-a[2])
            vx,vy,vz = (c[0]-a[0], c[1]-a[1], c[2]-a[2])
            nx,ny,nz = (uy*vz-uz*vy, uz*vx-ux*vz, ux*vy-uy*vx)
            l=(nx*nx+ny*ny+nz*nz)**0.5 or 1.0
            nx,ny,nz = nx/l,ny/l,nz/l
            f.write(f" facet normal {nx:.6f} {ny:.6f} {nz:.6f}\n  outer loop\n")
            f.write(f"   vertex {_tri_flat(a)}\n   vertex {_tri_flat(b)}\n   vertex {_tri_flat(c)}\n")
            f.write("  endloop\n endfacet\n")
        f.write(f"endsolid {name}\n")

def tube(R_out, wall_t, H, seg=96):
    R_in = max(R_out-wall_t, 1e-3)
    verts=[]; faces=[]
    for ring,(R,zoff) in enumerate(((R_out,0),(R_out,H),(R_in,H),(R_in,0))):
        for s in range(seg):
            ang=2*math.pi*s/seg
            x=R*math.cos(ang); y=R*math.sin(ang); z=zoff
            verts.append((x,y,z))
    # 바깥원통
    for s in range(seg):
        a=s; b=(s+1)%seg
        faces += [(a, b, seg+b), (a, seg+b, seg+a)]
    # 안쪽원통(뒤집힌 법선)
    off=2*seg
    for s in range(seg):
        a=off+s; b=off+(s+1)%seg
        faces += [(a, off+seg+b, b), (a, off+seg+a, off+seg+b)]
    # 위·아래 테두리 막기
    top_o=seg; top_i=2*seg
    for s in range(seg):
        a=top_o+s; b=top_o+(s+1)%seg; c=top_i+(s+1)%seg; d=top_i+s
        faces += [(a,b,c),(a,c,d)]
    bot_o=0; bot_i=3*seg
    for s in range(seg):
        a=bot_o+s; b=bot_i+(s+1)%seg; c=bot_i+s; d=bot_o+(s+1)%seg
        faces += [(a,b,c),(a,d,b)]
    return verts,faces

def cone(R, H, seg=64):
    verts=[(0,0,0)]
    for s in range(seg):
        ang=2*math.pi*s/seg
        verts.append((R*math.cos(ang), R*math.sin(ang), -H))
    faces=[]
    for s in range(1,seg+1):
        a=0; b=s; c=1 if s==seg else s+1
        faces.append((a,c,b))
    return verts,faces

@api.post("/cad/saturn_stage_build")
def saturn_stage_build(body:dict=Body(None)):
    p = body or {}
    stage = str(p.get("stage","S-IC")).upper()
    wall  = float(p.get("wall_t_mm",2.0))
    seg   = int(p.get("segments",96))
    # 근사(단위 mm)
    D33=10100.0; D21=6600.0
    L1,L2,L3 = 42100.0, 24900.0, 17800.0
    if stage=="S-IC":  R,H = D33/2, L1
    elif stage=="S-II": R,H = D33/2, L2
    else:               R,H = D21/2, L3
    run = RUNS/f"run-{datetime.now():%Y%m%d-%H%M%S}-{stage.replace('/','_')}"
    run.mkdir(parents=True, exist_ok=True)

    # Shell
    v,f = tube(R, wall, H, seg)
    shell = {"S-IC":"SIC_shell.stl","S-II":"SII_shell.stl","S-IVB":"SIVB_shell.stl"}[stage]
    write_ascii_stl(run/shell, v, f, name=f"{stage}_shell")

    # Engine placeholders
    if stage=="S-IC":
        ev,ef = cone(1800, 3000)   # F-1 근사
        write_ascii_stl(run/"F1_placeholder.stl", ev, ef, "F1")
    else:
        ev,ef = cone(1050, 2100)   # J-2 근사
        write_ascii_stl(run/"J2_placeholder.stl", ev, ef, "J2")

    meta={"ok":True,"stage":stage,"run_rel":str(run.relative_to(DATA)).replace("\\","/"),
          "parts":[x.name for x in run.iterdir() if x.suffix.lower()==".stl"]}
    (run/"meta.json").write_text(json.dumps(meta,indent=2),encoding="utf-8")
    return meta
