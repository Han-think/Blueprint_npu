from __future__ import annotations
from fastapi import APIRouter, Body
from pathlib import Path
from datetime import datetime
import math, json

api = APIRouter(prefix="/wb", tags=["saturn"])
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT/"data"
RUNS = DATA/"geometry/cad/saturn_cad_runs"
RUNS.mkdir(parents=True, exist_ok=True)

# ---------- 유틸 ----------
def _tri_flat(v): return " ".join(f"{a:.6f}" for a in v)
def write_ascii_stl(path:Path, verts, faces, name="part"):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        f.write(f"solid {name}\n")
        for (i,j,k) in faces:
            a,b,c=verts[i],verts[j],verts[k]
            ux,uy,uz=(b[0]-a[0], b[1]-a[1], b[2]-a[2])
            vx,vy,vz=(c[0]-a[0], c[1]-a[1], c[2]-a[2])
            nx,ny,nz=(uy*vz-uz*vy, uz*vx-ux*vz, ux*vy-uy*vx)
            l=(nx*nx+ny*ny+nz*nz)**0.5 or 1.0
            nx,ny,nz=nx/l,ny/l,nz/l
            f.write(f" facet normal {nx:.6f} {ny:.6f} {nz:.6f}\n  outer loop\n")
            f.write(f"   vertex {_tri_flat(a)}\n   vertex {_tri_flat(b)}\n   vertex {_tri_flat(c)}\n")
            f.write("  endloop\n endfacet\n")
        f.write(f"endsolid {name}\n")

def lathe_solid(profile, wall, seg=96):
    """profile: [(z, r_outer)...], z 오름차순(mm). 벽두께 wall(mm)로 내부/외부 돌출."""
    ro = profile
    ri = [(z, max(r-wall, 0.001)) for (z,r) in ro]
    rings_o=[]; rings_i=[]
    verts=[]; faces=[]
    # 외부/내부 링 생성
    for idx,(z,r) in enumerate(ro):
        ring=[]
        for s in range(seg):
            ang=2*math.pi*s/seg; x=r*math.cos(ang); y=r*math.sin(ang)
            ring.append(len(verts)); verts.append((x,y,z))
        rings_o.append(ring)
    for idx,(z,r) in enumerate(ri):
        ring=[]
        for s in range(seg):
            ang=2*math.pi*s/seg; x=r*math.cos(ang); y=r*math.sin(ang)
            ring.append(len(verts)); verts.append((x,y,z))
        rings_i.append(ring)
    # 외피
    for k in range(len(rings_o)-1):
        a=rings_o[k]; b=rings_o[k+1]
        for s in range(seg):
            s2=(s+1)%seg; faces += [(a[s], a[s2], b[s2]), (a[s], b[s2], b[s])]
    # 내피(법선 반전)
    off=len(rings_o)
    for k in range(len(rings_i)-1):
        a=rings_i[k]; b=rings_i[k+1]
        for s in range(seg):
            s2=(s+1)%seg; faces += [(b[s2], a[s2], a[s]), (b[s], b[s2], a[s])]
    # 바닥/상단 캡
    a=rings_o[0]; b=rings_i[0]
    for s in range(seg):
        s2=(s+1)%seg; faces += [(a[s], b[s2], b[s]), (a[s], a[s2], b[s2])]
    a=rings_o[-1]; b=rings_i[-1]
    for s in range(seg):
        s2=(s+1)%seg; faces += [(a[s], b[s], b[s2]), (a[s], b[s2], a[s2])]
    return verts,faces

def profile_tank(R, L_cyl, dome_h, z0=0.0):
    """반지름 R, 원통길이 L_cyl, 반구형 돔 높이 dome_h, 시작 z=z0"""
    pts=[]
    # 아래 돔
    for i in range(18):
        t=i/17
        z=z0 + dome_h*t
        r=(R**2 - (R-dome_h*t)**2)**0.5
        pts.append((z,r))
    # 원통
    pts.append((z0+dome_h, R))
    pts.append((z0+dome_h+L_cyl, R))
    # 위 돔
    for i in range(18):
        t=i/17
        z=z0+dome_h+L_cyl + dome_h*t
        r=(R**2 - (R - dome_h*(1-t))**2)**0.5
        pts.append((z,r))
    return pts

def make_tank(R, L_cyl, dome_h, wall, seg=96, z0=0.0):
    prof=profile_tank(R,L_cyl,dome_h,z0)
    return lathe_solid(prof, wall, seg)

def tube(R_out, wall, H, seg=96, z0=0.0):
    prof=[(z0, R_out), (z0+H, R_out)]
    return lathe_solid(prof, wall, seg)

def cone(R, H, seg=64, z0=0.0):
    # 엔진 더미
    verts=[(0,0,z0)]
    for s in range(seg):
        ang=2*math.pi*s/seg
        verts.append((R*math.cos(ang), R*math.sin(ang), z0-H))
    faces=[]
    for s in range(1,seg+1):
        a=0; b=s; c=1 if s==seg else s+1
        faces.append((a,c,b))
    return verts,faces

def fin_rect(R_out, span, chord, thick, z0, seg=24):
    """단순 사각핀 4개용: 원통 밖으로 수평 돌출"""
    # 한 장 생성( +X 방향 ), 나머지는 조립에서 회전 없이 4개 복제 대신 STL 하나로
    x0=R_out; x1=R_out+span; y0=-chord/2; y1=chord/2; z1=z0+thick
    v=[ (x0,y0,z0),(x1,y0,z0),(x1,y1,z0),(x0,y1,z0),
        (x0,y0,z1),(x1,y0,z1),(x1,y1,z1),(x0,y1,z1) ]
    f=[ (0,1,2),(0,2,3),(4,5,6),(4,6,7),
        (0,1,5),(0,5,4),(1,2,6),(1,6,5),
        (2,3,7),(2,7,6),(3,0,4),(3,4,7) ]
    return v,f

# ---------- 내부 설계 빌드 ----------
@api.post("/cad/saturn_stage_build")
def saturn_stage_build(body:dict=Body(None)):
    p = body or {}
    stage = str(p.get("stage","S-IC")).upper()
    seg   = int(p.get("segments",96))
    wall  = float(p.get("wall_t_mm",2.0))
    ribs  = int(p.get("stringers",24))
    # 기본 치수(mm) — 교육용 근사
    D33, D21 = 10100.0, 6600.0
    L1,L2,L3 = 42100.0, 24900.0, 17800.0
    if stage=="S-IC":
        Rstage, L = D33/2, L1
    elif stage=="S-II":
        Rstage, L = D33/2, L2
    else:
        Rstage, L = D21/2, L3

    run = RUNS/f"run-{datetime.now():%Y%m%d-%H%M%S}-{stage.replace('/','_')}"
    run.mkdir(parents=True, exist_ok=True)

    # 외피(셸)
    v,f = tube(Rstage, wall, L, seg, 0.0)
    write_ascii_stl(run/{"S-IC":"SIC_shell.stl","S-II":"SII_shell.stl","S-IVB":"SIVB_shell.stl"}[stage], v, f, f"{stage}_shell")

    if stage=="S-IC":
        # 분할 비율
        inter_h = 900.0
        l_lox = L*0.42
        l_rp1 = L - l_lox - inter_h
        # 탱크 반경(셸보다 여유)
        Rt = Rstage*0.92
        dome = Rt*0.55
        # LOX(위)
        v,f = make_tank(Rt, max(l_lox-2*dome, 1200.0), dome, wall, seg, z0=L-l_lox)
        write_ascii_stl(run/"SIC_LOX_tank.stl", v, f, "SIC_LOX")
        # 인터탱크(링+세로 보강)
        v,f = tube(Rstage, wall, inter_h, seg, z0=L-l_lox-900.0)
        write_ascii_stl(run/"SIC_Intertank_ring.stl", v, f, "SIC_INTER")
        # 간단 스트링거 N개(외부 작은 박스)
        span=120.0; chord=inter_h; thick=8.0
        for i in range(ribs):
            ang=2*math.pi*i/ribs
            x=(Rstage+2)*math.cos(ang); y=(Rstage+2)*math.sin(ang)
            # 박스를 원점 기준으로 만들고 평면이론상 회전 생략(프린트/보기용)
        # RP-1(아래)
        v,f = make_tank(Rt, max(l_rp1-2*dome, 1200.0), dome, wall, seg, z0=0.0)
        write_ascii_stl(run/"SIC_RP1_tank.stl", v, f, "SIC_RP1")
        # 추력 링(바닥)
        v,f = tube(Rstage*0.85, wall*4, 800.0, seg, z0=-800.0)
        write_ascii_stl(run/"SIC_Thrust_ring.stl", v, f, "SIC_THRUST")
        # 핀(사각 단순)
        v,f = fin_rect(Rstage, span=900.0, chord=1600.0, thick=120.0, z0=-600.0)
        write_ascii_stl(run/"SIC_Fin_rect.stl", v, f, "SIC_FIN")
        # 엔진 더미(F-1)
        v,f = cone(1800.0, 3000.0, 72, z0=-800.0)
        write_ascii_stl(run/"F1_placeholder.stl", v, f, "F1")

    elif stage=="S-II":
        # 공용 벌크헤드 구조(위 LOX, 아래 LH2)
        l_lox = L*0.22
        l_lh2 = L*0.73
        Rt = Rstage*0.9
        domeL = Rt*0.50
        # LOX 탱크(위)
        z_top = L - l_lox
        v,f = make_tank(Rt, max(l_lox-2*domeL, 900.0), domeL, wall, seg, z0=z_top)
        write_ascii_stl(run/"SII_LOX_tank.stl", v, f, "SII_LOX")
        # 공용 벌크헤드(두 돔 백투백)
        z_cb = L - l_lox + max(l_lox-2*domeL, 900.0) + domeL*0.6
        v1,f1 = lathe_solid(profile=[(z_cb-20, Rt),(z_cb, Rt*0.6)], wall=wall, seg=seg)  # 단순화
        write_ascii_stl(run/"SII_CommonBulkhead.stl", v1, f1, "SII_CB")
        # LH2(아래)
        v,f = make_tank(Rt*0.98, max(l_lh2-2*domeL, 1800.0), domeL, wall, seg, z0=0.0)
        write_ascii_stl(run/"SII_LH2_tank.stl", v, f, "SII_LH2")
        # 엔진 더미(J-2)
        v,f = cone(1050.0, 2100.0, 64, z0=-400.0)
        write_ascii_stl(run/"J2_placeholder.stl", v, f, "J2")

    else:  # S-IVB
        Rt = Rstage*0.9
        l_lox = L*0.26; l_lh2 = L*0.69
        domeL = Rt*0.48
        v,f = make_tank(Rt, max(l_lox-2*domeL, 700.0), domeL, wall, seg, z0=L-l_lox)
        write_ascii_stl(run/"SIVB_LOX_tank.stl", v, f, "S4B_LOX")
        v,f = make_tank(Rt*0.98, max(l_lh2-2*domeL, 1400.0), domeL, wall, seg, z0=0.0)
        write_ascii_stl(run/"SIVB_LH2_tank.stl", v, f, "S4B_LH2")
        v,f = cone(1050.0, 2100.0, 64, z0=-300.0)
        write_ascii_stl(run/"J2_placeholder.stl", v, f, "J2")

    meta={"ok":True,"stage":stage,"run_rel":str(run.relative_to(DATA)).replace("\\","/"),
          "parts":[x.name for x in sorted(run.iterdir()) if x.suffix.lower()==".stl"]}
    (run/"meta.json").write_text(json.dumps(meta,indent=2),encoding="utf-8")
    return meta
