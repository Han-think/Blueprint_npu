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

def lathe_solid(profile, wall, seg=128):
    ro = profile
    ri = [(z, max(r-wall, 0.001)) for (z,r) in ro]
    rings_o=[]; rings_i=[]
    verts=[]; faces=[]
    for (z,r) in ro:
        ring=[]; 
        for s in range(seg):
            ang=2*math.pi*s/seg; x=r*math.cos(ang); y=r*math.sin(ang)
            ring.append(len(verts)); verts.append((x,y,z))
        rings_o.append(ring)
    for (z,r) in ri:
        ring=[]; 
        for s in range(seg):
            ang=2*math.pi*s/seg; x=r*math.cos(ang); y=r*math.sin(ang)
            ring.append(len(verts)); verts.append((x,y,z))
        rings_i.append(ring)
    for k in range(len(rings_o)-1):
        a=rings_o[k]; b=rings_o[k+1]
        for s in range(seg):
            s2=(s+1)%seg; faces += [(a[s], a[s2], b[s2]), (a[s], b[s2], b[s])]
    for k in range(len(rings_i)-1):
        a=rings_i[k]; b=rings_i[k+1]
        for s in range(seg):
            s2=(s+1)%seg; faces += [(b[s2], a[s2], a[s]), (b[s], b[s2], a[s])]
    a=rings_o[0]; b=rings_i[0]
    for s in range(seg):
        s2=(s+1)%seg; faces += [(a[s], b[s2], b[s]), (a[s], a[s2], b[s2])]
    a=rings_o[-1]; b=rings_i[-1]
    for s in range(seg):
        s2=(s+1)%seg; faces += [(a[s], b[s], b[s2]), (a[s], b[s2], a[s2])]
    return verts,faces

def bezier3(p0,p1,p2,p3,t):
    u=1-t
    z = (u*u*u*p0[0] + 3*u*u*t*p1[0] + 3*u*t*t*p2[0] + t*t*t*p3[0])
    r = (u*u*u*p0[1] + 3*u*u*t*p1[1] + 3*u*t*t*p2[1] + t*t*t*p3[1])
    return (z,r)

def bell_profile(Rt, Re, L, theta_n_deg=30.0, theta_e_deg=7.0, n=64, z0=0.0):
    tn = math.tan(math.radians(theta_n_deg))
    te = math.tan(math.radians(theta_e_deg))
    p0=(z0, Rt)
    p3=(z0+L, Re)
    # C¹ 접선 일치(라오형 근사)
    p1=(z0 + L/3.0, Rt + (L/3.0)*tn)
    p2=(z0 + 2*L/3.0, Re - (L/3.0)*te)
    pts=[]
    for i in range(n+1):
        t=i/n
        pts.append(bezier3(p0,p1,p2,p3,t))
    return pts

def make_bell(Rt, Re, L, wall, seg=128, z0=0.0):
    prof = bell_profile(Rt, Re, L, z0=z0)
    return lathe_solid(prof, wall, seg)

def tube(R_out, wall, H, seg=128, z0=0.0):
    prof=[(z0, R_out), (z0+H, R_out)]
    return lathe_solid(prof, wall, seg)

def make_F1_engine(wall=2.0, seg=128, z0=-4200.0):
    # F-1: Re≈1850mm, L≈5800mm, eps=16 → Rt=Re/4≈462.5mm
    Re=1850.0; L=5800.0; Rt=Re/4.0
    v1,f1 = make_bell(Rt, Re, L, wall, seg, z0)
    # 필름쿨링 밴드(노즐 연장부 중단쯤)
    z_band = z0 + L*0.55
    v2,f2 = tube(Re*0.85, wall*4, 80.0, seg, z_band)
    # 단순 연소실/목(원통)
    v3,f3 = tube(Rt*1.15, wall*3, 400.0, seg, z0+L)
    V=v1+v2+v3; F = f1 + [(a+len(v1),b+len(v1),c+len(v1)) for (a,b,c) in f2] \
                 + [(a+len(v1)+len(v2),b+len(v1)+len(v2),c+len(v1)+len(v2)) for (a,b,c) in f3]
    return V,F

def make_J2_engine(wall=2.0, seg=128, z0=-3000.0):
    # J-2: Re≈1015mm, L≈3380mm, eps=27.5 → Rt≈Re/sqrt(27.5)
    Re=1015.0; L=3380.0; Rt=Re/(27.5**0.5)
    v1,f1 = make_bell(Rt, Re, L, wall, seg, z0)
    z_band = z0 + L*0.55
    v2,f2 = tube(Re*0.80, wall*4, 60.0, seg, z_band)
    v3,f3 = tube(Rt*1.20, wall*3, 320.0, seg, z0+L)
    V=v1+v2+v3; F = f1 + [(a+len(v1),b+len(v1),c+len(v1)) for (a,b,c) in f2] \
                 + [(a+len(v1)+len(v2),b+len(v1)+len(v2),c+len(v1)+len(v2)) for (a,b,c) in f3]
    return V,F

@api.post("/cad/saturn_stage_build")
def saturn_stage_build(body:dict=Body(None)):
    p = body or {}
    stage = str(p.get("stage","S-IC")).upper()
    seg   = int(p.get("segments",128))
    wall  = float(p.get("wall_t_mm",2.0))
    ribs  = int(p.get("stringers",24))

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

    v,f = tube(Rstage, wall, L, seg, 0.0)
    write_ascii_stl(run/{"S-IC":"SIC_shell.stl","S-II":"SII_shell.stl","S-IVB":"SIVB_shell.stl"}[stage], v, f, f"{stage}_shell")

    if stage=="S-IC":
        inter_h = 900.0
        l_lox = L*0.42
        l_rp1 = L - l_lox - inter_h
        Rt = Rstage*0.92; dome = Rt*0.55
        # LOX(위)
        v,f = lathe_solid(profile=[(L-l_lox, Rt),(L-l_lox+dome*0.3, Rt)], wall=wall, seg=seg)  # 짧은 프렙
        v,f = make_bell(Rt*0.0+Rt, Rt*0.0+Rt, 0.0, wall, seg, L-l_lox)  # no-op keep profile alive
        v,f = make_bell(1,1,1,wall,seg,L-l_lox)[:2]  # placeholder to keep locals
        v,f = make_bell.__globals__['lathe_solid'](profile=[(L-l_lox, Rt),(L-l_lox+max(l_lox-2*dome,1200.0), Rt)], wall=wall, seg=seg)
        write_ascii_stl(run/"SIC_LOX_tank.stl", v, f, "SIC_LOX")
        # 인터탱크
        v,f = tube(Rstage, wall, inter_h, seg, z0=L-l_lox-900.0)
        write_ascii_stl(run/"SIC_Intertank_ring.stl", v, f, "SIC_INTER")
        # RP-1(아래)
        v,f = make_bell.__globals__['lathe_solid'](profile=[(0.0, Rt),(max(l_rp1-2*dome,1200.0), Rt)], wall=wall, seg=seg)
        write_ascii_stl(run/"SIC_RP1_tank.stl", v, f, "SIC_RP1")
        # 추력 링
        v,f = tube(Rstage*0.85, wall*4, 800.0, seg, z0=-800.0)
        write_ascii_stl(run/"SIC_Thrust_ring.stl", v, f, "SIC_THRUST")
        # 핀
        x0=Rstage; x1=Rstage+900.0; y0=-800.0; y1=800.0; z0f=-600.0; z1f=-480.0
        v=[(x0,y0,z0f),(x1,y0,z0f),(x1,y1,z0f),(x0,y1,z0f),(x0,y0,z1f),(x1,y0,z1f),(x1,y1,z1f),(x0,y1,z1f)]
        f=[(0,1,2),(0,2,3),(4,5,6),(4,6,7),(0,1,5),(0,5,4),(1,2,6),(1,6,5),(2,3,7),(2,7,6),(3,0,4),(3,4,7)]
        write_ascii_stl(run/"SIC_Fin_rect.stl", v, f, "SIC_FIN")
        # F-1 5기
        v,f = make_F1_engine(wall, seg, z0=-5800.0)
        write_ascii_stl(run/"F1_nozzle.stl", v, f, "F1")
    elif stage=="S-II":
        l_lox = L*0.22; l_lh2 = L*0.73
        Rt = Rstage*0.9; domeL = Rt*0.50
        z_top = L - l_lox
        v,f = make_bell.__globals__['lathe_solid'](profile=[(z_top, Rt),(z_top+max(l_lox-2*domeL, 900.0), Rt)], wall=wall, seg=seg)
        write_ascii_stl(run/"SII_LOX_tank.stl", v, f, "SII_LOX")
        z_cb = L - l_lox + max(l_lox-2*domeL, 900.0) + domeL*0.6
        v1,f1 = lathe_solid(profile=[(z_cb-20, Rt),(z_cb, Rt*0.6)], wall=wall, seg=seg)
        write_ascii_stl(run/"SII_CommonBulkhead.stl", v1, f1, "SII_CB")
        v,f = make_bell.__globals__['lathe_solid'](profile=[(0.0, Rt*0.98),(max(l_lh2-2*domeL, 1800.0), Rt*0.98)], wall=wall, seg=seg)
        write_ascii_stl(run/"SII_LH2_tank.stl", v, f, "SII_LH2")
        v,f = make_J2_engine(wall, seg, z0=-3380.0)
        write_ascii_stl(run/"J2_nozzle.stl", v, f, "J2")
    else:
        Rt = Rstage*0.9; l_lox = L*0.26; l_lh2 = L*0.69; domeL = Rt*0.48
        v,f = make_bell.__globals__['lathe_solid'](profile=[(L-l_lox, Rt),(L-l_lox+max(l_lox-2*domeL, 700.0), Rt)], wall=wall, seg=seg)
        write_ascii_stl(run/"SIVB_LOX_tank.stl", v, f, "S4B_LOX")
        v,f = make_bell.__globals__['lathe_solid'](profile=[(0.0, Rt*0.98),(max(l_lh2-2*domeL, 1400.0), Rt*0.98)], wall=wall, seg=seg)
        write_ascii_stl(run/"SIVB_LH2_tank.stl", v, f, "S4B_LH2")
        v,f = make_J2_engine(wall, seg, z0=-3380.0)
        write_ascii_stl(run/"J2_nozzle.stl", v, f, "J2")

    meta={"ok":True,"stage":stage,"run_rel":str(run.relative_to(DATA)).replace("\\","/"),
          "parts":[x.name for x in sorted(run.iterdir()) if x.suffix.lower()==".stl"]}
    (run/"meta.json").write_text(json.dumps(meta,indent=2),encoding="utf-8")
    return meta
