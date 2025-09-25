# app/j58_twin.py  — twin cold-run demo with belt (ring) starter drive
from __future__ import annotations
from fastapi import APIRouter, Body
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import numpy as np, os, json, datetime, trimesh as tm

BASE_DIR = os.path.join("data","geometry","cad","j58_twin_runs")
os.makedirs(BASE_DIR, exist_ok=True)

CLR = 0.2   # 조립 여유(mm)

# ---------- basic solids (no boolean subtractions) ----------
def cyl(r:float, h:float, z0:float=0.0, sections:int=96)->tm.Trimesh:
    m = tm.creation.cylinder(radius=r, height=h, sections=sections)
    m.apply_translation([0,0,z0+h*0.5]); return m

def frustum(r0:float, r1:float, h:float, z0:float=0.0, sections:int=96, cap:bool=True)->tm.Trimesh:
    ang = np.linspace(0, 2*np.pi, sections, endpoint=False)
    c,s = np.cos(ang), np.sin(ang)
    vb = np.column_stack([r0*c, r0*s, np.full_like(c, z0)])
    vt = np.column_stack([r1*c, r1*s, np.full_like(c, z0+h)])
    V = np.vstack([vb, vt]); n=len(ang); F=[]
    for i in range(n):
        j=(i+1)%n; a,b=i,j; c_=n+j; d=n+i
        F += [[a,b,c_],[a,c_,d]]
    if cap and r0>1e-6:
        cb=len(V); V=np.vstack([V,[0,0,z0]])
        for i in range(n): j=(i+1)%n; F.append([cb,j,i])
    if cap and r1>1e-6:
        ct=len(V); V=np.vstack([V,[0,0,z0+h]])
        for i in range(n): j=(i+1)%n; F.append([ct,n+i,n+j])
    return tm.Trimesh(vertices=V, faces=np.asarray(F), process=True)

def cone(r0:float, r1:float, h:float, z0:float=0.0, sections:int=96)->tm.Trimesh:
    if hasattr(tm.creation, "conical_frustum"):
        m = tm.creation.conical_frustum(radius_top=r1, radius_bottom=r0, height=h, sections=sections)
        m.apply_translation([0,0,z0+h*0.5]); return m
    return frustum(r0, r1, h, z0, sections, cap=True)

def tube(r_in: float, r_out: float, h: float, z0: float=0.0, sections:int=96) -> tm.Trimesh:
    assert r_out > r_in >= 0 and h > 0
    ang = np.linspace(0, 2*np.pi, sections, endpoint=False)
    c, s = np.cos(ang), np.sin(ang)
    ob = np.column_stack([r_out*c, r_out*s, np.full_like(c, z0)])
    ot = np.column_stack([r_out*c, r_out*s, np.full_like(c, z0+h)])
    ib = np.column_stack([r_in*c,  r_in*s,  np.full_like(c, z0)])
    it = np.column_stack([r_in*c,  r_in*s,  np.full_like(c, z0+h)])
    V = np.vstack([ob, ot, ib, it]); n=len(ang)
    def q2t(a,b,c,d): return [[a,b,c],[a,c,d]]
    F=[]
    for i in range(n):
        j=(i+1)%n
        F += q2t(i, j, n+j, n+i)             # outer
        F += q2t(2*n+i, 3*n+i, 3*n+j, 2*n+j) # inner
        F += q2t(i, 2*n+j, 2*n+i, j)         # bottom
        F += q2t(n+i, 3*n+i, 3*n+j, n+j)     # top
    return tm.Trimesh(vertices=V, faces=np.asarray(F), process=True)

# ---------- rotors / stators (concat only) ----------
def blade_ring(n:int, r_root:float, r_tip:float, thick:float, z0:float, twist_deg:float, hub_r_in:float, hub_r_out:float)->tm.Trimesh:
    hub = tube(hub_r_in, hub_r_out, thick, z0)
    parts=[hub]
    b_w, b_t, b_h = (r_tip-r_root)*0.22, thick*1.2, (r_tip-r_root)*0.9
    for k in range(n):
        ang = 2*np.pi*k/n
        b = tm.creation.box(extents=[b_w, b_t, b_h])
        b.apply_translation([r_root+(r_tip-r_root)*0.55, 0, z0+thick*0.5])
        b.apply_transform(tm.transformations.rotation_matrix(np.deg2rad(twist_deg), [0,0,1]))
        b.apply_transform(tm.transformations.rotation_matrix(ang, [0,0,1]))
        parts.append(b)
    return tm.util.concatenate(parts)

def stator_ring(n:int, r_root:float, r_tip:float, thick:float, z0:float, twist_deg:float)->tm.Trimesh:
    ring = tube(r_root, r_tip, thick, z0)
    parts=[ring]
    b_w, b_t, b_h = (r_tip-r_root)*0.18, thick*1.1, (r_tip-r_root)*0.7
    for k in range(n):
        ang = 2*np.pi*k/n
        b = tm.creation.box(extents=[b_w, b_t, b_h])
        b.apply_translation([r_root+(r_tip-r_root)*0.5, 0, z0+thick*0.5])
        b.apply_transform(tm.transformations.rotation_matrix(np.deg2rad(twist_deg), [0,0,1]))
        b.apply_transform(tm.transformations.rotation_matrix(ang, [0,0,1]))
        parts.append(b)
    return tm.util.concatenate(parts)

# ---------- drive: shaft / spacers / pulley (belt) ----------
def shaft_5mm(L:float, z0:float)->tm.Trimesh:
    return cyl((5.0/2.0 - 0.05), L, z0)

def spacer_5mm(th:float, od:float, z0:float)->tm.Trimesh:
    return tube( (5.0/2.0 + 0.05), od/2.0, th, z0)

def v_pulley(bore:float=5.0, od:float=24.0, th:float=8.0, z0:float=0.0)->tm.Trimesh:
    hub = tube(bore*0.5+0.05, max(bore*0.5+0.05+2.0, od*0.25), th*0.6, z0+th*0.2)
    rim = cyl(od*0.5, th*0.5, z0+th*0.25)
    fl1 = frustum(od*0.5, od*0.45, th*0.25, z0+0.0)
    fl2 = frustum(od*0.45, od*0.5, th*0.25, z0+th*0.75)
    return tm.util.concatenate([hub,rim,fl1,fl2])

def bearing_holder(od=16.0, id=5.0, w=5.0, wall=4.0, z0=0.0)->tm.Trimesh:
    rin = (od/2.0)+CLR
    rout = rin + wall
    return tube(rin, rout, w+1.0, z0)

def bearing_rail(r_casing_inner:float, h:float, z0:float)->tm.Trimesh:
    rout = r_casing_inner - 0.6
    rin  = rout - 2.5
    return tube(rin, rout, h, z0)

# ---------- params ----------
class TwinParam(BaseModel):
    L_total: float=280.0
    R_casing: float=26.0
    N_fan: int=10
    N_comp: int=12
    N_turb: int=14
    eps: float=10.0
    nacelle_gap: float=90.0   # 좌/우 엔진 중심 간 거리(mm)
    pulley_od: float=24.0     # 벨트(고무 O링 등)용 풀리 외경
    starter_pulley_od: float=18.0

# ---------- one engine core, then translate on X ----------
def build_core(prefix:str, p:TwinParam, xoff:float)->list[tuple[str, tm.Trimesh]]:
    L,R,z = p.L_total, p.R_casing, 0.0
    parts=[]
    Ls=L*0.12; parts.append((f"{prefix}_inlet_spike.stl", cone(R*0.01, R*0.34, Ls, z))); z += Ls*0.9
    th=L*0.02; Hrs=th

    parts.append((f"{prefix}_fan_rotor.stl",   blade_ring(p.N_fan, 0.25*R,0.92*R, Hrs, z,  16, hub_r_in=2.5+0.05, hub_r_out=7.5))); z += Hrs*1.1
    parts.append((f"{prefix}_fan_stator.stl",  stator_ring(p.N_fan,0.30*R,0.94*R, Hrs*0.8, z,-12)));                                                    z += Hrs
    parts.append((f"{prefix}_comp_rotor.stl",  blade_ring(p.N_comp,0.20*R,0.90*R, Hrs, z,  22, hub_r_in=2.5+0.05, hub_r_out=7.0))); z += Hrs*1.1
    parts.append((f"{prefix}_comp_stator.stl", stator_ring(p.N_comp,0.26*R,0.91*R, Hrs*0.8, z,-14)));                                                    z += Hrs

    Lc=L*0.20; parts.append((f"{prefix}_combustor_shell.stl", tube(0.65*R, 0.93*R, Lc, z))); z += Lc
    parts.append((f"{prefix}_turb_rotor.stl",  blade_ring(p.N_turb,0.22*R,0.86*R, Hrs, z,  18, hub_r_in=2.5+0.05, hub_r_out=7.0))); z += Hrs*1.1
    parts.append((f"{prefix}_turb_stator.stl", stator_ring(p.N_turb,0.28*R,0.87*R, Hrs*0.8, z,-10)));                                                    z += Hrs

    Lab=L*0.16; parts.append((f"{prefix}_afterburner_shell.stl", tube(0.86*R, 0.96*R, Lab, z))); z += Lab
    Ln=L*0.16; At=np.pi*(0.35*R)**2; Re=np.sqrt((p.eps*At)/np.pi); parts.append((f"{prefix}_nozzle_cone.stl", cone(0.35*R, Re, Ln, z))); z += Ln
    parts.append((f"{prefix}_outer_casing.stl", tube(0.97*R, R, L, 0.0)))

    # shaft + pulley + bearing supports
    parts.append((f"{prefix}_shaft_5mm.stl", shaft_5mm(L*0.88, 0.06*L)))
    parts.append((f"{prefix}_pulley.stl", v_pulley(5.0, p.pulley_od, th*0.9, z0=0.12*L)))
    parts.append((f"{prefix}_bearing_holder_L.stl", bearing_holder(od=16, id=5, w=5, wall=4, z0=0.07*L)))
    parts.append((f"{prefix}_bearing_holder_R.stl", bearing_holder(od=16, id=5, w=5, wall=4, z0=0.93*L)))
    r_in_casing = 0.97*R
    parts.append((f"{prefix}_bearing_rail_L.stl",   bearing_rail(r_in_casing, h=6, z0=0.065*L)))
    parts.append((f"{prefix}_bearing_rail_R.stl",   bearing_rail(r_in_casing, h=6, z0=0.925*L)))

    # translate all by xoff
    out=[]
    for nm, m in parts:
        mm = m.copy()
        mm.apply_translation([xoff,0,0])
        out.append((nm, mm))
    return out

def build_twin(p:TwinParam)->dict:
    run = "run-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = os.path.join(BASE_DIR, run); os.makedirs(out_dir, exist_ok=True)

    gap = p.nacelle_gap
    L  = p.L_total
    # L/R engines
    parts  = []
    parts += build_core("L", p, -gap/2.0)
    parts += build_core("R", p,  gap/2.0)

    # starter (center) — small pulley on center shaft (use 5mm rod or print)
    parts.append(("START_center_pulley.stl", v_pulley(5.0, p.starter_pulley_od, L*0.02, z0=0.50*L)))
    parts.append(("START_center_shaft.stl",  shaft_5mm(L*0.25, 0.40*L)))

    # export
    bom=[]; sc=tm.Scene()
    for name,m in parts:
        path = os.path.join(out_dir, name); m.export(path)
        bom.append({"name":name,"path":path,"faces":int(m.faces.shape[0])})
        sc.add_geometry(m)
    glb = os.path.join(out_dir, "j58_twin_assembly.glb"); sc.export(glb)

    meta={"params":p.model_dump(),"parts":bom,"glb":glb,"out_dir":out_dir}
    with open(os.path.join(out_dir,"j58_twin_bom.json"),"w",encoding="utf-8") as f: json.dump(meta, f, ensure_ascii=False, indent=2)
    with open(os.path.join(BASE_DIR,"_last.json"),"w",encoding="utf-8") as f: json.dump(meta, f, ensure_ascii=False, indent=2)
    return {"ok":True, **meta}

def _safe(rel_path:str):
    base = os.path.abspath("data")
    full = os.path.abspath(os.path.join(base, rel_path.replace("/", os.sep)))
    if not full.startswith(base) or not os.path.exists(full): return None
    return full

api = APIRouter(prefix="/wb")

@api.get("/cad/j58_twin_demo")
def twin_demo(): return build_twin(TwinParam())

@api.post("/cad/j58_twin")
def twin_build(p:TwinParam=Body(...)): return build_twin(p)

@api.get("/cad/j58_twin_last")
def twin_last():
    p=os.path.join(BASE_DIR,"_last.json")
    return json.load(open(p,encoding="utf-8")) if os.path.exists(p) else {"ok":False,"reason":"no_run"}

@api.get("/files/{rel_path:path}")
def send_file(rel_path:str):
    full=_safe(rel_path)
    if not full: return JSONResponse({"ok":False,"reason":"not_found","rel":rel_path}, status_code=404)
    return FileResponse(full)
