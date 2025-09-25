from __future__ import annotations
from fastapi import APIRouter
from fastapi.responses import JSONResponse
import os, math, datetime, json

api = APIRouter(prefix="/wb", tags=["saturn"])
RUNS = os.path.join("data","geometry","cad","saturn_cad_runs")
os.makedirs(RUNS, exist_ok=True)

def _save_stl(path:str, tris:list[tuple[tuple[float,float,float],tuple[float,float,float],tuple[float,float,float]]]):
    with open(path, "w", encoding="utf-8") as f:
        nm = os.path.basename(path)
        f.write(f"solid {nm}\n")
        for a,b,c in tris:
            f.write("  facet normal 0 0 0\n    outer loop\n")
            f.write(f"      vertex {a[0]:.6f} {a[1]:.6f} {a[2]:.6f}\n")
            f.write(f"      vertex {b[0]:.6f} {b[1]:.6f} {b[2]:.6f}\n")
            f.write(f"      vertex {c[0]:.6f} {c[1]:.6f} {c[2]:.6f}\n")
            f.write("    endloop\n  endfacet\n")
        f.write(f"endsolid {nm}\n")

def _circle(r:float, z:float, n:int):
    return [(r*math.cos(2*math.pi*i/n), r*math.sin(2*math.pi*i/n), z) for i in range(n)]

def _tube(r_out:float, r_in:float, h:float, n:int):
    o0=_circle(r_out,0,n); o1=_circle(r_out,h,n)
    i0=_circle(r_in,0,n);  i1=_circle(r_in,h,n)
    tris=[]
    for i in range(n):
        j=(i+1)%n
        # outer wall
        tris += [(o0[i],o0[j],o1[i]), (o1[i],o0[j],o1[j])]
        # inner wall (flip)
        tris += [(i1[i],i0[j],i0[i]), (i1[j],i0[j],i1[i])]
        # top annulus
        tris += [(o1[i],o1[j],i1[i]), (i1[i],o1[j],i1[j])]
        # bottom annulus
        tris += [(o0[j],o0[i],i0[i]), (o0[j],i0[i],i0[j])]
    return tris

def _cone(r_base:float, h:float, n:int):
    base=_circle(r_base,0,n); apex=(0.0,0.0,h)
    tris=[]
    for i in range(n):
        j=(i+1)%n
        tris += [(base[i], base[j], apex)]           # side
        tris += [((0.0,0.0,0.0), base[j], base[i])]  # base cap
    return tris

def _emit_part(out_dir:str, name:str, tris):
    path = os.path.join(out_dir, name)
    _save_stl(path, tris)
    rel  = os.path.relpath(path, start=os.path.abspath("data")).replace("\\","/")
    return {"name":name, "path":path, "rel":rel}

@api.post("/cad/saturn_cad_build")
def saturn_cad_build(p:dict|None=None):
    p = p or {}
    n     = int(p.get("segments", 96))
    t_mm  = float(p.get("wall_t_mm", 2.0))

    # meters -> mm
    D_SIC = float(p.get("D_SIC_m",10.1))*1000.0
    L_SIC = float(p.get("L_SIC_m",42.1))*1000.0
    D_SII = float(p.get("D_SII_m",10.1))*1000.0
    L_SII = float(p.get("L_SII_m",24.9))*1000.0
    D_S4B = float(p.get("D_SIVB_m",6.60))*1000.0
    L_S4B = float(p.get("L_SIVB_m",17.8))*1000.0

    out = os.path.join(RUNS, "run-"+datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))
    os.makedirs(out, exist_ok=True)

    parts=[]
    parts.append(_emit_part(out, "SIC_shell.stl",  _tube(D_SIC/2, D_SIC/2 - t_mm, L_SIC, n)))
    parts.append(_emit_part(out, "SII_shell.stl",  _tube(D_SII/2, D_SII/2 - t_mm, L_SII, n)))
    parts.append(_emit_part(out, "SIVB_shell.stl", _tube(D_S4B/2, D_S4B/2 - t_mm, L_S4B, n)))
    # interstages (simple rings)
    inter_h = 900.0
    parts.append(_emit_part(out, "inter_SII_SIC.stl",  _tube(D_SII/2, D_SII/2 - t_mm, inter_h, n)))
    parts.append(_emit_part(out, "inter_SIVB_SII.stl", _tube(D_SII/2, D_SII/2 - t_mm, inter_h, n)))
    # engine placeholders
    parts.append(_emit_part(out, "F1_placeholder.stl", _cone(1850.0, 3000.0, n)))  # ~3.7 m dia
    parts.append(_emit_part(out, "J2_placeholder.stl", _cone(1050.0, 2200.0, n)))  # ~2.1 m dia

    meta = {"ok":True,"params":p,"parts":[{"name":x["name"],"rel":x["rel"]} for x in parts]}
    with open(os.path.join(out,"meta.json"),"w",encoding="utf-8") as f:
        json.dump(meta,f,indent=2)
    run_rel = os.path.relpath(out, start=os.path.abspath("data")).replace("\\","/")
    return {"ok":True,"run_rel":run_rel,"parts":parts}
