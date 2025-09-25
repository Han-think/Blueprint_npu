from __future__ import annotations
from fastapi import APIRouter, Body
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import numpy as np, os, json, datetime, trimesh as tm

BASE_DIR = os.path.join("data","geometry","cad","j58_runs")
os.makedirs(BASE_DIR, exist_ok=True)

CLR = 0.15  # 조립 여유(mm)

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
        for i in range(n):
            j=(i+1)%n; F.append([cb,j,i])
    if cap and r1>1e-6:
        ct=len(V); V=np.vstack([V,[0,0,z0+h]])
        for i in range(n):
            j=(i+1)%n; F.append([ct,n+i,n+j])
    return tm.Trimesh(vertices=V, faces=np.asarray(F), process=True)

def cyl(r:float, h:float, z0:float=0.0, sections:int=96)->tm.Trimesh:
    m = tm.creation.cylinder(radius=r, height=h, sections=sections)
    m.apply_translation([0,0,z0+h*0.5]); return m

def cone(r0:float, r1:float, h:float, z0:float=0.0, sections:int=96)->tm.Trimesh:
    if hasattr(tm.creation, "conical_frustum"):
        m = tm.creation.conical_frustum(radius_top=r1, radius_bottom=r0, height=h, sections=sections)
        m.apply_translation([0,0,z0+h*0.5]); return m
    return frustum(r0, r1, h, z0=z0, sections=sections, cap=True)

def blade_ring(n:int, r_root:float, r_tip:float, thick:float, z0:float, twist_deg:float, hub_r_in:float, hub_r_out:float)->tm.Trimesh:
    # 허브 = 튜브(샤프트 관통), 림 = 없음(프린트 용이)
    hub = tube(hub_r_in, hub_r_out, thick, z0)
    parts = [hub]
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

def bearing_holder(od=16.0, id=5.0, w=5.0, wall=4.0, z0=0.0)->tm.Trimesh:
    rin = (od/2.0)+CLR     # 베어링 외경이 들어갈 구멍
    rout = rin + wall
    return tube(rin, rout, w+1.0, z0)

def bearing_rail(r_casing_inner:float, h:float, z0:float)->tm.Trimesh:
    # 외피 안쪽에 끼워지는 레일(링)
    rout = r_casing_inner - (0.6)   # 억지끼움 방지
    rin  = rout - 2.5
    return tube(rin, rout, h, z0)

def shaft_5mm(L:float, z0:float)->tm.Trimesh:
    return cyl((5.0/2.0 - 0.05), L, z0)  # 살짝 슬림

def spacer_5mm(th:float, od:float, z0:float)->tm.Trimesh:
    return tube( (5.0/2.0 + 0.05), od/2.0, th, z0)

class J58Param(BaseModel):
    L_total: float=300.0
    R_casing: float=30.0
    N_fan: int=12
    N_comp: int=14
    N_turb: int=16
    eps: float=12.0

def build_j58(p:J58Param)->dict:
    run = "run-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = os.path.join(BASE_DIR, run); os.makedirs(out_dir, exist_ok=True)

    L,R,z = p.L_total, p.R_casing, 0.0
    parts = []

    # (A) 외피/인렛/노즐 (프린트 단순화)
    Ls = L*0.12; parts.append(("inlet_spike.stl", cone(R*0.01, R*0.34, Ls, z))); z += Ls*0.9
    th = L*0.02
    # 로터/스테이터 모듈 두께
    Hrs = th
    # 팬 로터/스테이터
    parts.append(("fan_rotor.stl",   blade_ring(p.N_fan, 0.25*R,0.95*R, Hrs, z,  16, hub_r_in=2.5+0.05, hub_r_out=8.0))); z += Hrs*1.1
    parts.append(("fan_stator.stl",  stator_ring(p.N_fan,0.30*R,0.96*R, Hrs*0.8, z,-12)));                            z += Hrs
    # 컴프 로터/스테이터
    parts.append(("comp_rotor.stl",  blade_ring(p.N_comp,0.20*R,0.92*R, Hrs, z,  22, hub_r_in=2.5+0.05, hub_r_out=7.5))); z += Hrs*1.1
    parts.append(("comp_stator.stl", stator_ring(p.N_comp,0.26*R,0.93*R, Hrs*0.8, z,-14)));                            z += Hrs

    # 연소실(모형) – 콜드런이므로 단순 쉘
    Lc = L*0.20; parts.append(("combustor_shell.stl", tube(0.65*R, 0.95*R, Lc, z))); z += Lc

    # 터빈 로터/스테이터
    parts.append(("turb_rotor.stl",  blade_ring(p.N_turb,0.22*R,0.88*R, Hrs, z,  18, hub_r_in=2.5+0.05, hub_r_out=7.5))); z += Hrs*1.1
    parts.append(("turb_stator.stl", stator_ring(p.N_turb,0.28*R,0.89*R, Hrs*0.8, z,-10)));                            z += Hrs

    # 애프터버너 쉘
    Lab = L*0.18; parts.append(("afterburner_shell.stl", tube(0.88*R, 0.98*R, Lab, z))); z += Lab

    # 노즐
    Ln = L*0.18; At = np.pi*(0.35*R)**2; Re = np.sqrt((p.eps*At)/np.pi)
    parts.append(("nozzle_cone.stl", cone(0.35*R, Re, Ln, z))); z += Ln

    # 외피(끝에 한 번)
    parts.append(("outer_casing.stl", tube(0.97*R, R, L, 0.0)))

    # (B) 구동계(콜드런): 5mm 샤프트 + 스페이서 + 베어링 홀더/레일
    # 샤프트: 전체 길이의 90%
    parts.append(("shaft_5mm.stl", shaft_5mm(L*0.9, 0.05*L)))
    # 스페이서(로터 사이 간격)
    sp_th = Hrs*0.6; sp_od = 16.0
    z_sp = 0.05*L + Hrs*0.6
    for i, nm in enumerate(["spacer1","spacer2","spacer3","spacer4","spacer5"]):
        parts.append((f"{nm}.stl", spacer_5mm(sp_th, sp_od, z_sp))); z_sp += sp_th*1.2

    # 베어링(625ZZ: 5x16x5) 홀더 + 레일
    r_in_casing = 0.97*R
    parts.append(("bearing_holder_L.stl", bearing_holder(od=16, id=5, w=5, wall=4, z0=0.07*L)))
    parts.append(("bearing_holder_R.stl", bearing_holder(od=16, id=5, w=5, wall=4, z0=0.93*L)))
    parts.append(("bearing_rail_L.stl",   bearing_rail(r_in_casing, h=6, z0=0.065*L)))
    parts.append(("bearing_rail_R.stl",   bearing_rail(r_in_casing, h=6, z0=0.925*L)))

    # 저장
    bom=[]; sc=tm.Scene()
    for name,m in parts:
        path = os.path.join(out_dir, name); m.export(path)
        bom.append({"name":name,"faces":int(m.faces.shape[0]),"path":path}); sc.add_geometry(m)
    glb = os.path.join(out_dir, "j58_assembly.glb"); sc.export(glb)

    meta={"params":p.model_dump(),"parts":bom,"glb":glb,"out_dir":out_dir}
    with open(os.path.join(out_dir,"j58_bom.json"),"w",encoding="utf-8") as f: json.dump(meta, f, ensure_ascii=False, indent=2)
    with open(os.path.join(BASE_DIR,"_last.json"),"w",encoding="utf-8") as f: json.dump(meta, f, ensure_ascii=False, indent=2)
    return {"ok":True, **meta}

def _safe_data_path(rel_path:str):
    base = os.path.abspath("data")
    full = os.path.abspath(os.path.join(base, rel_path.replace("/", os.sep)))
    if not full.startswith(base) or not os.path.exists(full): return None
    return full

api = APIRouter(prefix="/wb")

@api.get("/cad/j58_demo")
def j58_demo(): return build_j58(J58Param())

@api.post("/cad/j58")
def j58_build(p:J58Param=Body(...)): return build_j58(p)

@api.get("/cad/j58_last")
def j58_last():
    p=os.path.join(BASE_DIR,"_last.json")
    return json.load(open(p,encoding="utf-8")) if os.path.exists(p) else {"ok":False,"reason":"no_run"}

@api.get("/files/{rel_path:path}")
def send_file(rel_path:str):
    full=_safe_data_path(rel_path)
    if not full:
        return JSONResponse({"ok":False,"reason":"not_found","rel":rel_path}, status_code=404)
    return FileResponse(full)
