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
    rings_o=[]; rings_i=[]; verts=[]; faces=[]
    for (z,r) in ro:
        ring=[]
        for s in range(seg):
            ang=2*math.pi*s/seg; x=r*math.cos(ang); y=r*math.sin(ang)
            ring.append(len(verts)); verts.append((x,y,z))
        rings_o.append(ring)
    for (z,r) in ri:
        ring=[]
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

def tube(R_out, wall, H, seg=128, z0=0.0):
    return lathe_solid([(z0,R_out),(z0+H,R_out)], wall, seg)

def bell_profile(Rt, Re, L, theta_n=30.0, theta_e=7.0, n=64, z0=0.0):
    tn=math.tan(math.radians(theta_n)); te=math.tan(math.radians(theta_e))
    p0=(z0,Rt); p3=(z0+L,Re)
    p1=(z0+L/3.0, Rt + (L/3.0)*tn)
    p2=(z0+2*L/3.0, Re - (L/3.0)*te)
    pts=[]; 
    for i in range(n+1):
        t=i/n; u=1-t
        z=(u**3*p0[0] + 3*u*u*t*p1[0] + 3*u*t*t*p2[0] + t**3*p3[0])
        r=(u**3*p0[1] + 3*u*u*t*p1[1] + 3*u*t*t*p2[1] + t**3*p3[1])
        pts.append((z,r))
    return pts

def make_bell(Rt, Re, L, wall, seg=128, z0=0.0):
    return lathe_solid(bell_profile(Rt,Re,L,z0=z0), wall, seg)

def make_tank_profile(R, L_cyl, dome_h, z0=0.0):
    pts=[]
    for i in range(18):
        t=i/17; z=z0 + dome_h*t; r=(R**2 - (R-dome_h*t)**2)**0.5
        pts.append((z,r))
    pts.append((z0+dome_h,R)); pts.append((z0+dome_h+L_cyl,R))
    for i in range(18):
        t=i/17; z=z0+dome_h+L_cyl + dome_h*t; r=(R**2 - (R - dome_h*(1-t))**2)**0.5
        pts.append((z,r))
    return pts

def make_tank(R, L_cyl, dome_h, wall, seg=128, z0=0.0):
    return lathe_solid(make_tank_profile(R,L_cyl,dome_h,z0), wall, seg)

# ── 엔진 서브컴포넌트(1단계 근사) ──
def f1_parts(wall=2.0, seg=128, z0=-5800.0):
    Re=1850.0; L=5800.0; Rt=Re/4.0
    parts=[]
    v,f = make_bell(Rt,Re,L,wall,seg,z0); parts.append(("F1_nozzle.stl",v,f))
    v,f = tube(Rt*1.25, wall*3, 280.0, seg, z0+L) ; parts.append(("F1_chamber.stl",v,f))
    v,f = tube(Re*0.82, wall*4, 80.0, seg, z0+L*0.55); parts.append(("F1_manifold.stl",v,f))
    v,f = tube(Re*0.50, wall*6, 60.0, seg, z0+L+180.0); parts.append(("F1_injector.stl",v,f))
    v,f = tube(Re*0.35, wall*6, 120.0, seg, z0-60.0); parts.append(("F1_gimbal_ring.stl",v,f))
    return parts

def j2_parts(wall=2.0, seg=128, z0=-3380.0):
    Re=1015.0; L=3380.0; Rt=Re/(27.5**0.5)
    parts=[]
    v,f = make_bell(Rt,Re,L,wall,seg,z0); parts.append(("J2_nozzle.stl",v,f))
    v,f = tube(Rt*1.30, wall*3, 220.0, seg, z0+L); parts.append(("J2_chamber.stl",v,f))
    v,f = tube(Re*0.78, wall*4, 60.0, seg, z0+L*0.55); parts.append(("J2_manifold.stl",v,f))
    v,f = tube(Re*0.45, wall*6, 50.0, seg, z0+L+160.0); parts.append(("J2_injector.stl",v,f))
    return parts

@api.post("/cad/saturn_stage_build")
def saturn_stage_build(body:dict=Body(None)):
    p = body or {}
    stage = str(p.get("stage","S-IC")).upper()
    seg   = int(p.get("segments",128))
    wall  = float(p.get("wall_t_mm",2.0))
    ribs  = int(p.get("stringers",24))

    D33,D21=10100.0,6600.0; L1,L2,L3=42100.0,24900.0,17800.0
    if stage=="S-IC": Rstage,L=D33/2,L1
    elif stage=="S-II": Rstage,L=D33/2,L2
    else: Rstage,L=D21/2,L3

    run = RUNS/f"run-{datetime.now():%Y%m%d-%H%M%S}-{stage.replace('/','_')}"
    run.mkdir(parents=True, exist_ok=True)

    v,f = tube(Rstage, wall, L, seg, 0.0)
    write_ascii_stl(run/{"S-IC":"SIC_shell.stl","S-II":"SII_shell.stl","S-IVB":"SIVB_shell.stl"}[stage], v, f, f"{stage}_shell")

    if stage=="S-IC":
        inter_h=900.0; l_lox=L*0.42; l_rp1=L-l_lox-inter_h
        Rt=Rstage*0.92; dome=Rt*0.55
        v,f = make_tank(Rt, max(l_lox-2*dome,1200.0), dome, wall, seg, z0=L-l_lox)
        write_ascii_stl(run/"SIC_LOX_tank.stl", v, f, "SIC_LOX")
        v,f = tube(Rstage, wall, inter_h, seg, z0=L-l_lox-900.0)
        write_ascii_stl(run/"SIC_Intertank_ring.stl", v, f, "SIC_INTER")
        v,f = make_tank(Rt, max(l_rp1-2*dome,1200.0), dome, wall, seg, z0=0.0)
        write_ascii_stl(run/"SIC_RP1_tank.stl", v, f, "SIC_RP1")
        v,f = tube(Rstage*0.85, wall*4, 800.0, seg, z0=-800.0)
        write_ascii_stl(run/"SIC_Thrust_ring.stl", v, f, "SIC_THRUST")
        # 핀(사각)
        x0=Rstage; x1=Rstage+900.0; y0=-800.0; y1=800.0; z0f=-600.0; z1f=-480.0
        v=[(x0,y0,z0f),(x1,y0,z0f),(x1,y1,z0f),(x0,y1,z0f),(x0,y0,z1f),(x1,y0,z1f),(x1,y1,z1f),(x0,y1,z1f)]
        f=[(0,1,2),(0,2,3),(4,5,6),(4,6,7),(0,1,5),(0,5,4),(1,2,6),(1,6,5),(2,3,7),(2,7,6),(3,0,4),(3,4,7)]
        write_ascii_stl(run/"SIC_Fin_rect.stl", v, f, "SIC_FIN")
        # F-1 서브컴포넌트
        for name,vf in f1_parts(wall,seg,z0=-5800.0):
            v,f=vf; write_ascii_stl(run/name, v, f, name[:-4])
    elif stage=="S-II":
        l_lox=L*0.22; l_lh2=L*0.73; Rt=Rstage*0.9; domeL=Rt*0.50
        z_top=L-l_lox
        v,f = make_tank(Rt, max(l_lox-2*domeL,900.0), domeL, wall, seg, z0=z_top)
        write_ascii_stl(run/"SII_LOX_tank.stl", v, f, "SII_LOX")
        z_cb = L - l_lox + max(l_lox-2*domeL, 900.0) + domeL*0.6
        v1,f1 = lathe_solid([(z_cb-20, Rt),(z_cb, Rt*0.6)], wall, seg)
        write_ascii_stl(run/"SII_CommonBulkhead.stl", v1, f1, "SII_CB")
        v,f = make_tank(Rt*0.98, max(l_lh2-2*domeL,1800.0), domeL, wall, seg, z0=0.0)
        write_ascii_stl(run/"SII_LH2_tank.stl", v, f, "SII_LH2")
        for name,vf in j2_parts(wall,seg,z0=-3380.0):
            v,f=vf; write_ascii_stl(run/name, v, f, name[:-4])
    else:
        Rt=Rstage*0.9; l_lox=L*0.26; l_lh2=L*0.69; domeL=Rt*0.48
        v,f = make_tank(Rt, max(l_lox-2*domeL,700.0), domeL, wall, seg, z0=L-l_lox)
        write_ascii_stl(run/"SIVB_LOX_tank.stl", v, f, "S4B_LOX")
        v,f = make_tank(Rt*0.98, max(l_lh2-2*domeL,1400.0), domeL, wall, seg, z0=0.0)
        write_ascii_stl(run/"SIVB_LH2_tank.stl", v, f, "S4B_LH2")
        for name,vf in j2_parts(wall,seg,z0=-3380.0):
            v,f=vf; write_ascii_stl(run/name, v, f, name[:-4])

    meta={"ok":True,"stage":stage,"run_rel":str(run.relative_to(DATA)).replace("\\","/"),
          "parts":[x.name for x in sorted(run.iterdir()) if x.suffix.lower()==".stl"]}
    (run/"meta.json").write_text(json.dumps(meta,indent=2),encoding="utf-8")
    return meta
