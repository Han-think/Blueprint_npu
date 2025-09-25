from __future__ import annotations
from fastapi import APIRouter, Body
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import numpy as np, os, json, datetime, trimesh as tm

BASE_DIR = os.path.join("data","geometry","cad","j58_twin_v2_runs")
os.makedirs(BASE_DIR, exist_ok=True)

# ===== 공차/규격 =====
CLR = 0.20     # 일반 조립 여유(mm)
SHAFT = 5.00   # 샤프트 기준
BE_OD = 16.00  # 625ZZ 외경
BE_W  = 5.00   # 625ZZ 두께

# ===== 기본 프리미티브(보올리언 없이) =====
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

# ===== 블레이드/링 =====
def blade_ring(n:int, r_root:float, r_tip:float, thick:float, z0:float, twist:float, hub_r_in:float, hub_r_out:float)->tm.Trimesh:
    hub = tube(hub_r_in, hub_r_out, thick, z0)
    parts=[hub]
    b_w, b_t, b_h = (r_tip-r_root)*0.22, thick*1.2, (r_tip-r_root)*0.9
    for k in range(n):
        ang = 2*np.pi*k/n
        b = tm.creation.box(extents=[b_w, b_t, b_h])
        b.apply_translation([r_root+(r_tip-r_root)*0.55, 0, z0+thick*0.5])
        b.apply_transform(tm.transformations.rotation_matrix(np.deg2rad(twist), [0,0,1]))
        b.apply_transform(tm.transformations.rotation_matrix(ang, [0,0,1]))
        parts.append(b)
    return tm.util.concatenate(parts)

def stator_ring(n:int, r_root:float, r_tip:float, thick:float, z0:float, twist:float)->tm.Trimesh:
    ring = tube(r_root, r_tip, thick, z0)
    parts=[ring]
    b_w, b_t, b_h = (r_tip-r_root)*0.18, thick*1.1, (r_tip-r_root)*0.7
    for k in range(n):
        ang = 2*np.pi*k/n
        b = tm.creation.box(extents=[b_w, b_t, b_h])
        b.apply_translation([r_root+(r_tip-r_root)*0.5, 0, z0+thick*0.5])
        b.apply_transform(tm.transformations.rotation_matrix(np.deg2rad(twist), [0,0,1]))
        b.apply_transform(tm.transformations.rotation_matrix(ang, [0,0,1]))
        parts.append(b)
    return tm.util.concatenate(parts)

# ===== 드라이브/지지 =====
def shaft_5mm(L:float, z0:float)->tm.Trimesh:
    return cyl((SHAFT/2.0 - 0.05), L, z0)

def spacer_5mm(th:float, od:float, z0:float)->tm.Trimesh:
    return tube((SHAFT/2.0 + 0.05), od/2.0, th, z0)

def v_pulley(bore:float=SHAFT, od:float=24.0, th:float=8.0, z0:float=0.0)->tm.Trimesh:
    hub = tube(bore*0.5+0.05, max(bore*0.5+0.05+2.0, od*0.25), th*0.6, z0+th*0.2)
    rim = cyl(od*0.5, th*0.5, z0+th*0.25)
    fl1 = frustum(od*0.5,  od*0.45, th*0.25, z0+0.00)
    fl2 = frustum(od*0.45, od*0.50, th*0.25, z0+0.75*th)
    return tm.util.concatenate([hub,rim,fl1,fl2])

def bearing_holder(od=BE_OD, id=SHAFT, w=BE_W, wall=4.0, z0=0.0)->tm.Trimesh:
    rin = (od*0.5)+CLR
    rout = rin + wall
    return tube(rin, rout, w+1.0, z0)

def bearing_rail(r_casing_inner:float, h:float, z0:float)->tm.Trimesh:
    rout = r_casing_inner - 0.6
    rin  = rout - 2.5
    return tube(rin, rout, h, z0)

# ===== 세그먼트 외피 & 커플러 & 시트 =====
def casing_shell(r_out:float, th:float, L:float, z0:float)->tm.Trimesh:
    return tube(r_out-th, r_out, L, z0)

def coupler_sleeve(r_out:float, th:float, L:float, z0:float)->tm.Trimesh:
    # 분할면을 덮는 외부 슬리브(살짝 큰 지름 + 얇은 벽)
    return tube(r_out-th*0.6, r_out+0.3, L, z0)

def seat_ring(r_in:float, r_out:float, th:float, z0:float)->tm.Trimesh:
    # 스테이터 받침(얇은 링)
    return tube(r_in, r_out, th, z0)

# ===== 파라미터 =====
class TwinP(BaseModel):
    L_total: float=280.0
    R_casing: float=26.0
    wall: float=2.2
    N_fan: int=10
    N_comp: int=12
    N_turb: int=14
    eps: float=10.0
    nacelle_gap: float=90.0
    pulley_od: float=24.0
    starter_pulley_od: float=18.0

# ===== 코어 한 쪽 빌드(세그먼트/시트 포함) =====
def build_core(prefix:str, p:TwinP, xoff:float)->list[tuple[str, tm.Trimesh]]:
    L,R,z = p.L_total, p.R_casing, 0.0
    wall = p.wall
    parts=[]

    # 세그먼트 길이
    Lf, Lm, La = L*0.34, L*0.32, L*0.34
    gap_sleeve = 8.0  # 커플러 슬리브 길이

    # (0) 인렛/노즐
    Ls=L*0.12; parts.append((f"{prefix}_inlet_spike.stl", cone(R*0.01, R*0.34, Ls, z))); z += Ls*0.9
    Ln=L*0.16; At=np.pi*(0.35*R)**2; Re=np.sqrt((p.eps*At)/np.pi)

    # (1) 외피 세그먼트
    z0_front = 0.0
    parts.append((f"{prefix}_casing_front.stl", casing_shell(R, wall, Lf, z0_front)))
    z0_mid = z0_front + Lf
    parts.append((f"{prefix}_casing_mid.stl",   casing_shell(R, wall, Lm, z0_mid)))
    z0_aft = z0_mid + Lm
    parts.append((f"{prefix}_casing_aft.stl",   casing_shell(R, wall, La, z0_aft)))

    # (1-1) 커플러 슬리브(외부에서 쑥 끼워 체결)
    parts.append((f"{prefix}_coupler_FM.stl",   coupler_sleeve(R, wall, gap_sleeve, z0_mid - gap_sleeve*0.5)))
    parts.append((f"{prefix}_coupler_MA.stl",   coupler_sleeve(R, wall, gap_sleeve, z0_aft - gap_sleeve*0.5)))

    # (2) 팬/컴프/터빈 로터·스테이터 + 시트 링(스테이터 받침)
    th_stage = L*0.02
    r_in_cas = R - wall
    # 프론트 구간 내 배치
    z_stage = 0.08*L
    parts.append((f"{prefix}_seat_fan.stl",  seat_ring(0.26*R, r_in_cas-CLR, th_stage*0.35, z_stage-0.5*th_stage)))
    parts.append((f"{prefix}_fan_rotor.stl",   blade_ring(p.N_fan, 0.25*R,0.92*R, th_stage, z_stage,  16, hub_r_in=SHAFT*0.5+0.05, hub_r_out=7.5))); z_stage += th_stage*1.1
    parts.append((f"{prefix}_fan_stator.stl",  stator_ring(p.N_fan,0.30*R,0.94*R, th_stage*0.8, z_stage,-12)));                                            z_stage += th_stage*0.9

    parts.append((f"{prefix}_seat_comp.stl", seat_ring(0.22*R, r_in_cas-CLR, th_stage*0.35, z_stage-0.5*th_stage)))
    parts.append((f"{prefix}_comp_rotor.stl",  blade_ring(p.N_comp,0.20*R,0.90*R, th_stage, z_stage,  22, hub_r_in=SHAFT*0.5+0.05, hub_r_out=7.0))); z_stage += th_stage*1.1
    parts.append((f"{prefix}_comp_stator.stl", stator_ring(p.N_comp,0.26*R,0.91*R, th_stage*0.8, z_stage,-14)));                                            z_stage += th_stage*0.9

    # 미드 구간에 연소실(모형)
    z_comb = z0_mid + 0.05*L
    Lc=L*0.18; parts.append((f"{prefix}_combustor_shell.stl", tube(0.65*R, r_in_cas-CLR, Lc, z_comb)))

    # 애프트 구간에 터빈
    z_turb = z0_aft + 0.05*L
    parts.append((f"{prefix}_seat_turb.stl",  seat_ring(0.24*R, r_in_cas-CLR, th_stage*0.35, z_turb-0.5*th_stage)))
    parts.append((f"{prefix}_turb_rotor.stl",  blade_ring(p.N_turb,0.22*R,0.86*R, th_stage, z_turb,  18, hub_r_in=SHAFT*0.5+0.05, hub_r_out=7.0))); z_turb += th_stage*1.1
    parts.append((f"{prefix}_turb_stator.stl", stator_ring(p.N_turb,0.28*R,0.87*R, th_stage*0.8, z_turb,-10)))

    # 노즐(애프트 끝)
    parts.append((f"{prefix}_nozzle_cone.stl", cone(0.35*R, Re, Ln, z0_aft + La - Ln)))

    # (3) 샤프트/스페이서/풀리/베어링 지지
    parts.append((f"{prefix}_shaft_5mm.stl", shaft_5mm(L*0.88, 0.06*L)))
    parts.append((f"{prefix}_pulley.stl",    v_pulley(SHAFT, od=24.0, th=th_stage*0.9, z0=0.12*L)))
    parts.append((f"{prefix}_bearing_holder_L.stl", bearing_holder(od=BE_OD, id=SHAFT, w=BE_W, wall=4, z0=0.07*L)))
    parts.append((f"{prefix}_bearing_holder_R.stl", bearing_holder(od=BE_OD, id=SHAFT, w=BE_W, wall=4, z0=0.93*L)))
    parts.append((f"{prefix}_bearing_rail_L.stl",   bearing_rail(r_in_cas, h=6, z0=0.065*L)))
    parts.append((f"{prefix}_bearing_rail_R.stl",   bearing_rail(r_in_cas, h=6, z0=0.925*L)))

    # X 오프셋 적용
    out=[]
    for nm, m in parts:
        mm = m.copy(); mm.apply_translation([xoff,0,0]); out.append((nm, mm))
    return out

# ===== 트윈 빌드 =====
def build_twin_v2(p:TwinP)->dict:
    run = "run-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = os.path.join(BASE_DIR, run); os.makedirs(out_dir, exist_ok=True)

    parts  = []
    parts += build_core("L", p, -p.nacelle_gap/2.0)
    parts += build_core("R", p,  p.nacelle_gap/2.0)

    # 중앙 스타터(풀리+샤프트)
    L = p.L_total
    parts.append(("START_center_pulley.stl", v_pulley(SHAFT, od=p.starter_pulley_od, th=L*0.02, z0=0.50*L)))
    parts.append(("START_center_shaft.stl",  shaft_5mm(L*0.25, 0.40*L)))

    # 내보내기
    bom=[]; sc=tm.Scene()
    for name,m in parts:
        path = os.path.join(out_dir, name); m.export(path)
        bom.append({"name":name,"path":path,"faces":int(m.faces.shape[0])})
        sc.add_geometry(m)
    glb = os.path.join(out_dir, "j58_twin_v2_assembly.glb"); sc.export(glb)

    meta={"params":p.model_dump(),"parts":bom,"glb":glb,"out_dir":out_dir}
    with open(os.path.join(out_dir,"j58_twin_v2_bom.json"),"w",encoding="utf-8") as f: json.dump(meta, f, ensure_ascii=False, indent=2)
    with open(os.path.join(BASE_DIR,"_last.json"),"w",encoding="utf-8") as f: json.dump(meta, f, ensure_ascii=False, indent=2)
    return {"ok":True, **meta}

def _safe(rel_path:str):
    base = os.path.abspath("data")
    full = os.path.abspath(os.path.join(base, rel_path.replace("/", os.sep)))
    if not full.startswith(base) or not os.path.exists(full): return None
    return full

api = APIRouter(prefix="/wb")

@api.get("/cad/j58_twin_v2_demo")
def twin_v2_demo(): return build_twin_v2(TwinP())

@api.post("/cad/j58_twin_v2")
def twin_v2_build(p:TwinP=Body(...)): return build_twin_v2(p)

@api.get("/cad/j58_twin_v2_last")
def twin_v2_last():
    p=os.path.join(BASE_DIR,"_last.json")
    return json.load(open(p,encoding="utf-8")) if os.path.exists(p) else {"ok":False,"reason":"no_run"}

@api.get("/files/{rel_path:path}")
def send_file(rel_path:str):
    base = os.path.abspath("data")
    full = os.path.abspath(os.path.join(base, rel_path.replace("/", os.sep)))
    if not full.startswith(base) or not os.path.exists(full):
        return JSONResponse({"ok":False,"reason":"not_found","rel":rel_path}, status_code=404)
    return FileResponse(full)
# ===== V2.1 ADD-ON: calibration + jigs + belt tension bits =====
import math

M3 = 3.0
PILOT = 1.6  # 드릴 파일럿 지름(추천)

def calib_cube(size=20.0, z0=0.0):
    return tm.creation.box(extents=[size, size, size]).apply_translation([0,0,z0+size*0.5]) or tm.creation.box()

def calib_tube(od=20.0, id=10.0, h=8.0, z0=0.0):
    return tube(id*0.5, od*0.5, h, z0)

def pilot_peg(r:float, h:float, z0:float, ang:float):
    p = cyl(PILOT*0.5, h, z0)
    p.apply_translation([r,0,z0+h*0.5])
    p.apply_transform(tm.transformations.rotation_matrix(ang, [0,0,1]))
    return p

def jig_ring_with_pilots(name_prefix:str, R:float, wall:float, z:float, n:int=6, width:float=4.0):
    base = tube(R-wall, R+0.4, width, z)
    parts=[base]
    r_peg = R+0.6
    for k in range(n):
        ang = 2*math.pi*k/n
        parts.append(pilot_peg(r_peg, width, z, ang))
    return tm.util.concatenate(parts)

def belt_idler(m3_clear=0.2, od=10.0, th=6.0, z0=0.0):
    # M3 관통(튜브 코어) + 외륜
    return tube((M3*0.5 + m3_clear), od*0.5, th, z0)

def strap_anchor(w=22.0, t=6.0, z0=0.0):
    # 지퍼타이 고정용 작은 앵커(두 개 프린트해서 벨트 아이들러와 함께 사용)
    body = tm.creation.box(extents=[w, 8.0, t]); body.apply_translation([0,0,z0+t*0.5])
    bridge = tm.creation.box(extents=[w*0.8, 3.2, t*0.6]); bridge.apply_translation([0,0,z0+t*0.3])
    bridge2= tm.creation.box(extents=[w*0.8, 3.2, t*0.6]); bridge2.apply_translation([0,0,z0+t*0.8])
    return tm.util.concatenate([body, bridge, bridge2])

def build_calibration_pack()->dict:
    run = "calib-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = os.path.join(BASE_DIR, run); os.makedirs(out_dir, exist_ok=True)
    parts = []
    parts.append(("calib_cube_20mm.stl",    calib_cube(20.0, 0.0)))
    parts.append(("calib_tube_od20_id10.stl", calib_tube(od=20.0, id=10.0, h=8.0, z0=22.0)))
    bom=[]; sc=tm.Scene()
    for name,m in parts:
        path=os.path.join(out_dir,name); m.export(path); bom.append({"name":name,"path":path,"faces":int(m.faces.shape[0])}); sc.add_geometry(m)
    glb=os.path.join(out_dir,"calib_pack.glb"); sc.export(glb)
    meta={"kind":"calibration","parts":bom,"glb":glb,"out_dir":out_dir,"note":"인쇄 후 실제 치수 측정 → CLR(조립여유) 보정 권장"}
    with open(os.path.join(out_dir,"meta.json"),"w",encoding="utf-8") as f: json.dump(meta,f,ensure_ascii=False,indent=2)
    return {"ok":True, **meta}

def build_jigs_and_tension(p:TwinP)->dict:
    run = "jigs-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = os.path.join(BASE_DIR, run); os.makedirs(out_dir, exist_ok=True)
    L,R,wall = p.L_total, p.R_casing, p.wall
    parts=[]
    # 커플러 위치(본체와 동일 로직)
    Lf, Lm, La = L*0.34, L*0.32, L*0.34
    z0_front = 0.0
    z0_mid = z0_front + Lf
    z0_aft = z0_mid + Lm
    # 좌/우 공통 커플러 드릴가이드(외면 파일럿)
    parts.append(("JIG_coupler_FM.stl", jig_ring_with_pilots("FM", R, wall, z0_mid - 4.0, n=6, width=4.0)))
    parts.append(("JIG_coupler_MA.stl", jig_ring_with_pilots("MA", R, wall, z0_aft - 4.0, n=6, width=4.0)))
    # 시트(스테이터 받침) 위치 근처 가이드(외피 안쪽 기준이지만, 외면에 표시 후 뚫고 나사 사용 시 드릴지그로 충분)
    th_stage = L*0.02
    z_stage_front = 0.08*L
    parts.append(("JIG_seat_fan.stl",  jig_ring_with_pilots("SF", R, wall, z_stage_front-0.5*th_stage, n=4, width=3.5)))
    parts.append(("JIG_seat_comp.stl", jig_ring_with_pilots("SC", R, wall, z_stage_front+th_stage*1.9, n=4, width=3.5)))
    z_turb = z0_aft + 0.05*L
    parts.append(("JIG_seat_turb.stl", jig_ring_with_pilots("ST", R, wall, z_turb-0.5*th_stage, n=4, width=3.5)))
    # 벨트 텐셔너: 아이들러 + 앵커 블럭 2개(지퍼타이 고정)
    parts.append(("BELT_idler_M3.stl", belt_idler(m3_clear=0.25, od=10.0, th=6.0, z0=0.0)))
    parts.append(("BELT_anchor_A.stl", strap_anchor(22.0, 6.0, 0.0)))
    parts.append(("BELT_anchor_B.stl", strap_anchor(22.0, 6.0, 8.0)))
    # 내보내기
    bom=[]; sc=tm.Scene()
    for name,m in parts:
        path=os.path.join(out_dir,name); m.export(path); bom.append({"name":name,"path":path,"faces":int(m.faces.shape[0])}); sc.add_geometry(m)
    glb=os.path.join(out_dir,"jigs_pack.glb"); sc.export(glb)
    meta={"kind":"jigs+tension","parts":bom,"glb":glb,"out_dir":out_dir,
          "note":"커플러/시트 위치 표식용 파일럿, 외부 지그로 드릴 후 M3 체결 가능. 텐셔너는 아이들러+앵커+지퍼타이 사용."}
    with open(os.path.join(out_dir,"meta.json"),"w",encoding="utf-8") as f: json.dump(meta,f,ensure_ascii=False,indent=2)
    return {"ok":True, **meta}

@api.get("/cad/j58_twin_v2_calib")
def twin_v2_calib(): return build_calibration_pack()

@api.post("/cad/j58_twin_v2_jigs")
def twin_v2_jigs(p:TwinP=Body(TwinP())): return build_jigs_and_tension(p)
