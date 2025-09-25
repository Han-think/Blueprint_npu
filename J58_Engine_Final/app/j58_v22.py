from __future__ import annotations
from fastapi import APIRouter, Body
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import numpy as np, os, json, datetime, trimesh as tm

BASE_DIR = os.path.join("data","geometry","cad","j58_v22_runs")
os.makedirs(BASE_DIR, exist_ok=True)

CLR = 0.20  # 기본 조립 여유(mm)

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
        for i in range(n): j=(i+1)%n; F.append([cb,j,i])
    if cap and r1>1e-6:
        ct=len(V); V=np.vstack([V,[0,0,z0+h]])
        for i in range(n): j=(i+1)%n; F.append([ct,n+i,n+j])
    return tm.Trimesh(vertices=V, faces=np.asarray(F), process=True)

def cyl(r:float, h:float, z0:float=0.0, sections:int=96)->tm.Trimesh:
    m = tm.creation.cylinder(radius=r, height=h, sections=sections)
    m.apply_translation([0,0,z0+h*0.5]); return m

def cone(r0:float, r1:float, h:float, z0:float=0.0, sections:int=96)->tm.Trimesh:
    if hasattr(tm.creation, "conical_frustum"):
        m = tm.creation.conical_frustum(radius_top=r1, radius_bottom=r0, height=h, sections=sections)
        m.apply_translation([0,0,z0+h*0.5]); return m
    return frustum(r0, r1, h, z0=z0, sections=sections, cap=True)

def lug_box(r_out:float, w:float, t:float, h:float, z0:float, ang_deg:float)->tm.Trimesh:
    """외피 플랜지 근처 클램프용 러그(양쪽에서 클립/볼트로 죄기)"""
    b = tm.creation.box(extents=[w, t, h])
    # 러그 중심을 외경 바깥쪽으로
    b.apply_translation([r_out + t*0.5, 0, z0 + h*0.5])
    Rz = tm.transformations.rotation_matrix(np.deg2rad(ang_deg), [0,0,1])
    b.apply_transform(Rz)
    return b

def stator_seat(r_in:float, r_out:float, th:float, z0:float, tabs:int=3)->tm.Trimesh:
    """스테이터 수용 시트(내경쪽 얕은 링 + 바깥 탭 3개) — 탭은 접착 정렬용"""
    base = tube(r_in, r_out, th, z0)
    parts=[base]
    tab_w, tab_t, tab_h = (r_out-r_in)*0.35, (r_out-r_in)*0.60, th*0.9
    for k in range(tabs):
        ang = 360.0*k/tabs
        parts.append(lug_box(r_out, tab_w, tab_t, tab_h, z0, ang))
    return tm.util.concatenate(parts)

def blade_ring(n:int, r_root:float, r_tip:float, thick:float, z0:float, twist_deg:float,
               hub_r_in:float, hub_r_out:float)->tm.Trimesh:
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

def bearing_holder(od=16.0, id=5.0, w=5.0, wall=4.0, z0=0.0)->tm.Trimesh:
    rin = (od*0.5)+CLR
    rout = rin + wall
    return tube(rin, rout, w+1.0, z0)

def bearing_rail(r_casing_inner:float, h:float, z0:float)->tm.Trimesh:
    rout = r_casing_inner - 0.6
    rin  = rout - 2.5
    return tube(rin, rout, h, z0)

def shaft_5mm(L:float, z0:float)->tm.Trimesh:
    return cyl((5.0*0.5 - 0.05), L, z0)

def spacer_5mm(th:float, od:float, z0:float)->tm.Trimesh:
    return tube((5.0*0.5 + 0.05), od*0.5, th, z0)

class J58V22Param(BaseModel):
    L_total: float=300.0
    R_casing: float=30.0
    N_fan: int=12
    N_comp: int=14
    N_turb: int=16
    eps: float=12.0
    lug_count:int=6            # 각 플랜지 주변 러그 개수
    casing_split: tuple[float,float] | None = None
    # None→(0.33L, 0.66L) 기본 분할

def build_v22(p:J58V22Param)->dict:
    run = "run-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = os.path.join(BASE_DIR, run); os.makedirs(out_dir, exist_ok=True)

    L,R = p.L_total, p.R_casing
    splitA, splitB = (p.casing_split or (0.33*L, 0.66*L))
    z = 0.0
    parts=[]
    meta = {"params":p.model_dump()}

    # (A) 인렛/스파이크
    Ls = L*0.12
    parts.append(("inlet_spike.stl", cone(R*0.01, R*0.34, Ls, z))); z += Ls*0.9

    th_stage = L*0.02
    # 팬
    parts.append(("fan_rotor.stl",   blade_ring(p.N_fan,  0.25*R,0.95*R, th_stage, z, +16, hub_r_in=2.5+0.05, hub_r_out=8.0))); z += th_stage*1.1
    parts.append(("fan_stator.stl",  stator_ring(p.N_fan, 0.30*R,0.96*R, th_stage*0.8, z, -12)));                           z += th_stage

    # 컴프
    parts.append(("comp_rotor.stl",  blade_ring(p.N_comp, 0.20*R,0.92*R, th_stage, z, +22, hub_r_in=2.5+0.05, hub_r_out=7.5))); z += th_stage*1.1
    parts.append(("comp_stator.stl", stator_ring(p.N_comp,0.26*R,0.93*R, th_stage*0.8, z, -14)));                            z += th_stage

    # 연소부(모형)
    Lc = L*0.20
    parts.append(("combustor_shell.stl", tube(0.65*R, 0.95*R, Lc, z))); z += Lc

    # 터빈
    parts.append(("turb_rotor.stl",  blade_ring(p.N_turb,0.22*R,0.88*R, th_stage, z, +18, hub_r_in=2.5+0.05, hub_r_out=7.5))); z += th_stage*1.1
    parts.append(("turb_stator.stl", stator_ring(p.N_turb,0.28*R,0.89*R, th_stage*0.8, z, -10)));                            z += th_stage

    # 애프터버너(모형)
    Lab = L*0.18
    parts.append(("afterburner_shell.stl", tube(0.88*R, 0.98*R, Lab, z))); z += Lab

    # 노즐
    Ln = L*0.18; At = np.pi*(0.35*R)**2; Re = np.sqrt((p.eps*At)/np.pi)
    parts.append(("nozzle_cone.stl", cone(0.35*R, Re, Ln, z))); z += Ln

    # (B) 외피 3분할 + 플랜지 러그
    # front: [0, splitA], mid: [splitA, splitB], aft: [splitB, L]
    def casing_section(z0, z1, name):
        h = max(1.0, z1 - z0)
        shell = tube(0.97*R, R, h, z0)
        # 러그(양쪽 섹션 경계 근처에 p.lug_count 개)
        lugs=[]
        for k in range(p.lug_count):
            ang = 360.0*k/p.lug_count
            lugs.append(lug_box(R, w=8.0, t=3.2, h=6.0, z0=z0+1.5, ang_deg=ang))
            lugs.append(lug_box(R, w=8.0, t=3.2, h=6.0, z0=z1-7.5, ang_deg=ang))
        return (name, tm.util.concatenate([shell]+lugs))
    parts.append(casing_section(0.0,        splitA, "casing_front.stl"))
    parts.append(casing_section(splitA,     splitB, "casing_mid.stl"))
    parts.append(casing_section(splitB,     L,      "casing_aft.stl"))

    # (C) 스테이터 시트(외피 내부 정렬·접착용)
    seat_t = 2.0
    parts.append(("seat_fan.stl",  stator_seat(0.95*R-1.5, 0.97*R-0.2, seat_t, 0.12*L + 2.0)))
    parts.append(("seat_comp.stl", stator_seat(0.95*R-1.5, 0.97*R-0.2, seat_t, 0.12*L + 2.0 + th_stage*2.2 )))
    parts.append(("seat_turb.stl", stator_seat(0.95*R-1.5, 0.97*R-0.2, seat_t, 0.12*L + 2.0 + th_stage*2.2 + Lc + th_stage*2.2 )))

    # (D) 구동계(콜드런): 샤프트/스페이서/베어링
    parts.append(("shaft_5mm.stl", shaft_5mm(L*0.92, 0.04*L)))
    sp_th = th_stage*0.6; sp_od = 16.0
    z_sp  = 0.06*L
    for i in range(6):
        parts.append((f"spacer_{i+1}.stl", spacer_5mm(sp_th, sp_od, z_sp))); z_sp += sp_th*1.18
    r_in_casing = 0.97*R
    parts.append(("bearing_holder_L.stl", bearing_holder(od=16, id=5, w=5, wall=4, z0=0.07*L)))
    parts.append(("bearing_holder_R.stl", bearing_holder(od=16, id=5, w=5, wall=4, z0=0.93*L)))
    parts.append(("bearing_rail_L.stl",   bearing_rail(r_in_casing, h=6, z0=0.065*L)))
    parts.append(("bearing_rail_R.stl",   bearing_rail(r_in_casing, h=6, z0=0.925*L)))

    # 저장 + 장면
    bom=[]; sc=tm.Scene()
    for name,m in parts:
        path = os.path.join(out_dir, name); m.export(path)
        bom.append({"name":name,"faces":int(m.faces.shape[0]),"path":path})
        sc.add_geometry(m)
    glb = os.path.join(out_dir, "j58_v22_assembly.glb"); sc.export(glb)

    spec = {
        "standard": "J58-V2.2 coldrun (non-combustion)",
        "units": "mm",
        "clearance": {"fit": CLR, "shaft_bore_extra": 0.05},
        "fasteners": {"suggested": "M3", "notes": "러그 위치에 표식 기준 드릴"},
        "bearings": ["625ZZ 5x16x5 (x2)"],
        "print": {"min_wall": 2.4, "stage_base": 2.0, "shell_layers": "≥3", "infill": "20~35%"},
        "assembly_notes": [
            "외피 3분할+러그: 케이블타이 또는 M3 볼트로 클램프",
            "시트(seat_*)를 외피 안쪽에 접착→ 스테이터 고정",
            "로터 허브는 샤프트에 스페이서로 간격 유지 후 고정(접착/세트스크류 가공)"
        ]
    }

    meta={"params":(p.model_dump()),"parts":bom,"glb":glb,"out_dir":out_dir,"spec":spec}
    with open(os.path.join(out_dir,"j58_v22_bom.json"),"w",encoding="utf-8") as f: json.dump(meta, f, ensure_ascii=False, indent=2)
    with open(os.path.join(BASE_DIR,"_last.json"),"w",encoding="utf-8") as f: json.dump(meta, f, ensure_ascii=False, indent=2)
    return {"ok":True, **meta}

def _safe_data_path(rel_path:str):
    base = os.path.abspath("data")
    full = os.path.abspath(os.path.join(base, rel_path.replace("/", os.sep)))
    if not full.startswith(base) or not os.path.exists(full): return None
    return full

api = APIRouter(prefix="/wb")

@api.get("/cad/j58_v22_demo")
def j58_v22_demo(): return build_v22(J58V22Param())

@api.post("/cad/j58_v22")
def j58_v22_build(p:J58V22Param=Body(...)): return build_v22(p)

@api.get("/cad/j58_v22_last")
def j58_v22_last():
    p=os.path.join(BASE_DIR,"_last.json")
    return json.load(open(p,encoding="utf-8")) if os.path.exists(p) else {"ok":False,"reason":"no_run"}

@api.get("/cad/j58_v22_spec")
def j58_v22_spec():
    p=os.path.join(BASE_DIR,"_last.json")
    if not os.path.exists(p): return {"ok":False,"reason":"no_run"}
    return json.load(open(p,encoding="utf-8")).get("spec",{})

@api.get("/files/{rel_path:path}")
def send_file(rel_path:str):
    full=_safe_data_path(rel_path)
    if not full:
        return JSONResponse({"ok":False,"reason":"not_found","rel":rel_path}, status_code=404)
    return FileResponse(full)
