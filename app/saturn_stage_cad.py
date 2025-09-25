from __future__ import annotations
from fastapi import APIRouter
from fastapi.responses import JSONResponse
import os, math, datetime, json

api = APIRouter(prefix="/wb", tags=["saturn"])
RUNS = os.path.join("data","geometry","cad","saturn_cad_runs")
os.makedirs(RUNS, exist_ok=True)

def _save_stl(path, tris):
    with open(path,"w",encoding="utf-8") as f:
        f.write(f"solid {os.path.basename(path)}\n")
        for a,b,c in tris:
            f.write("  facet normal 0 0 0\n    outer loop\n")
            for v in (a,b,c): f.write(f"      vertex {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
            f.write("    endloop\n  endfacet\n")
        f.write(f"endsolid {os.path.basename(path)}\n")

def _circle(r,z,n): return [(r*math.cos(2*math.pi*i/n), r*math.sin(2*math.pi*i/n), z) for i in range(n)]
def _tube(r_out,r_in,h,n):
    o0=_circle(r_out,0,n); o1=_circle(r_out,h,n); i0=_circle(r_in,0,n); i1=_circle(r_in,h,n); T=[]
    for i in range(n):
        j=(i+1)%n
        T += [(o0[i],o0[j],o1[i]), (o1[i],o0[j],o1[j])]
        T += [(i1[i],i0[j],i0[i]), (i1[j],i0[j],i1[i])]
        T += [(o1[i],o1[j],i1[i]), (i1[i],o1[j],i1[j])]
        T += [(o0[j],o0[i],i0[i]), (o0[j],i0[i],i0[j])]
    return T
def _cone(r_base,h,n):
    base=_circle(r_base,0,n); apex=(0.0,0.0,h); T=[]
    for i in range(n):
        j=(i+1)%n
        T += [(base[i], base[j], apex)]
        T += [((0.0,0.0,0.0), base[j], base[i])]
    return T
def _emit(out_dir,name,tris):
    os.makedirs(out_dir,exist_ok=True); p=os.path.join(out_dir,name); _save_stl(p,tris)
    rel=os.path.relpath(p,start=os.path.abspath("data")).replace("\\","/")
    return {"name":name,"rel":rel,"path":p}

@api.post("/cad/saturn_stage_build")
def saturn_stage_build(body:dict|None=None):
    b = body or {}
    stage = str(b.get("stage","S-IC")).upper()   # S-IC / S-II / S-IVB
    n      = int(b.get("segments", 96))
    t_mm   = float(b.get("wall_t_mm", 2.0))
    D_SIC, L_SIC = 10.1*1000, 42.1*1000
    D_SII, L_SII = 10.1*1000, 24.9*1000
    D_S4B, L_S4B = 6.60*1000, 17.8*1000
    out = os.path.join(RUNS, f"run-{datetime.datetime.now():%Y%m%d-%H%M%S}-{stage.replace('/','_')}")
    parts=[]
    if stage=="S-IC":
        parts.append(_emit(out,"SIC_shell.stl", _tube(D_SIC/2, D_SIC/2 - t_mm, L_SIC, n)))
        parts.append(_emit(out,"intertank_ring.stl", _tube(D_SIC/2, D_SIC/2 - t_mm, 900.0, n)))
        parts.append(_emit(out,"F1_placeholder.stl", _cone(1850.0, 3000.0, n)))
    elif stage=="S-II":
        parts.append(_emit(out,"SII_shell.stl", _tube(D_SII/2, D_SII/2 - t_mm, L_SII, n)))
        parts.append(_emit(out,"J2_placeholder.stl", _cone(1050.0, 2200.0, n)))
    elif stage in ("S-IVB","SIVB","S-4B"):
        parts.append(_emit(out,"SIVB_shell.stl", _tube(D_S4B/2, D_S4B/2 - t_mm, L_S4B, n)))
        parts.append(_emit(out,"J2_placeholder.stl", _cone(1050.0, 2200.0, n)))
    else:
        return JSONResponse({"ok":False,"reason":"unknown_stage"}, status_code=400)
    meta={"ok":True,"stage":stage,"parts":[{"name":p["name"],"rel":p["rel"]} for p in parts]}
    with open(os.path.join(out,"meta.json"),"w",encoding="utf-8") as f: json.dump(meta,f,indent=2)
    run_rel=os.path.relpath(out,start=os.path.abspath("data")).replace("\\","/")
    return {"ok":True,"stage":stage,"run_rel":run_rel,"parts":parts}
