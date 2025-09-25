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

def _tri(a,b,c): return (a,b,c)
def _flat(v): return f"{v[0]:.6f} {v[1]:.6f} {v[2]:.6f}"
def write_ascii_stl(path:Path, tris, name="part"):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        f.write(f"solid {name}\n")
        for (a,b,c) in tris:
            ux,uy,uz=(b[0]-a[0], b[1]-a[1], b[2]-a[2])
            vx,vy,vz=(c[0]-a[0], c[1]-a[1], c[2]-a[2])
            nx,ny,nz=(uy*vz-uz*vy, uz*vx-ux*vz, ux*vy-uy*vx); L=(nx*nx+ny*ny+nz*nz)**0.5 or 1
            nx,ny,nz=nx/L,ny/L,nz/L
            f.write(f" facet normal {nx:.6f} {ny:.6f} {nz:.6f}\n  outer loop\n")
            f.write(f"   vertex {_flat(a)}\n   vertex {_flat(b)}\n   vertex {_flat(c)}\n")
            f.write("  endloop\n endfacet\n")
        f.write(f"endsolid {name}\n")

def lathe_solid(profile, wall, seg=128):
    ro=profile; ri=[(z, max(r-wall, 0.001)) for (z,r) in ro]
    def ring(r,z):
        return [(r*math.cos(2*math.pi*s/seg), r*math.sin(2*math.pi*s/seg), z) for s in range(seg)]
    vo=[ring(r,z) for (z,r) in ro]; vi=[ring(r,z) for (z,r) in ri]
    tris=[]
    for k in range(len(vo)-1):
        a=vo[k]; b=vo[k+1]
        for s in range(seg):
            s2=(s+1)%seg; tris += [_tri(a[s],a[s2],b[s2]), _tri(a[s],b[s2],b[s])]
    for k in range(len(vi)-1):
        a=vi[k]; b=vi[k+1]
        for s in range(seg):
            s2=(s+1)%seg; tris += [_tri(b[s2],a[s2],a[s]), _tri(b[s],b[s2],a[s])]
    a=vo[0]; b=vi[0]
    for s in range(seg):
        s2=(s+1)%seg; tris += [_tri(a[s],b[s2],b[s]), _tri(a[s],a[s2],b[s2])]
    a=vo[-1]; b=vi[-1]
    for s in range(seg):
        s2=(s+1)%seg; tris += [_tri(a[s],b[s],b[s2]), _tri(a[s],b[s2],a[s2])]
    return tris

def tube(R_out, wall, H, seg=128, z0=0.0):
    prof=[(z0, R_out),(z0+H, R_out)]
    return lathe_solid(prof, wall, seg)

def profile_tank(R, L_cyl, dome_h, z0=0.0):
    pts=[]
    for i in range(18):
        t=i/17; z=z0+dome_h*t; r=(R**2 - (R-dome_h*t)**2)**0.5
        pts.append((z,r))
    pts.append((z0+dome_h, R)); pts.append((z0+dome_h+L_cyl, R))
    for i in range(18):
        t=i/17; z=z0+dome_h+L_cyl + dome_h*t; r=(R**2 - (R - dome_h*(1-t))**2)**0.5
        pts.append((z,r))
    return pts

def make_tank(R, L_cyl, dome_h, wall, seg=128, z0=0.0):
    return lathe_solid(profile_tank(R,L_cyl,dome_h,z0), wall, seg)

def box(w,d,h, z0=0.0, cx=0.0, cy=0.0):
    x0=cx-w/2; x1=cx+w/2; y0=cy-d/2; y1=cy+d/2; z1=z0+h
    v=[(x0,y0,z0),(x1,y0,z0),(x1,y1,z0),(x0,y1,z0),(x0,y0,z1),(x1,y0,z1),(x1,y1,z1),(x0,y1,z1)]
    f=[(0,1,2),(0,2,3),(4,5,6),(4,6,7),(0,1,5),(0,5,4),(1,2,6),(1,6,5),(2,3,7),(2,7,6),(3,0,4),(3,4,7)]
    return [ (v[a],v[b],v[c]) for (a,b,c) in f ]

def cylinder(Ro, wall, H, z0):
    return tube(Ro, wall, H, 128, z0)

def cone(R_top, R_bot, H, seg=96, z0=0.0):
    tris=[]
    for s in range(seg):
        a=2*math.pi*s/seg; b=2*math.pi*((s+1)%seg)/seg
        v0=(R_top*math.cos(a), R_top*math.sin(a), z0)
        v1=(R_bot*math.cos(a), R_bot*math.sin(a), z0-H)
        v2=(R_bot*math.cos(b), R_bot*math.sin(b), z0-H)
        v3=(R_top*math.cos(b), R_top*math.sin(b), z0)
        tris += [_tri(v0,v2,v1), _tri(v0,v3,v2)]
    return tris

@api.post("/wb/cad/saturn_stage_build")
def saturn_stage_build(body:dict=Body(None)):
    p=body or {}; stage=str(p.get("stage","S-IC")).upper()
    seg=int(p.get("segments",128)); wall=float(p.get("wall_t_mm",2.0))
    RUN = RUNS/f"run-{datetime.now():%Y%m%d-%H%M%S}-{stage.replace('/','_')}"; RUN.mkdir(parents=True, exist_ok=True)
    D33, D21 = 10100.0, 6600.0
    L1,L2,L3 = 42100.0, 24900.0, 17800.0
    if stage=="S-IC": R,L = D33/2, L1
    elif stage=="S-II": R,L = D33/2, L2
    else: R,L = D21/2, L3

    # 공통 셸
    write_ascii_stl(RUN/{"S-IC":"SIC_shell.stl","S-II":"SII_shell.stl","S-IVB":"SIVB_shell.stl"}[stage], tube(R, wall, L, seg, 0.0), f"{stage}_shell")

    if stage=="S-IC":
        inter_h = 900.0
        l_lox = L*0.42; l_rp1 = L - l_lox - inter_h
        Rt = R*0.92; dome = Rt*0.55
        write_ascii_stl(RUN/"SIC_RP1_tank.stl", make_tank(Rt, max(l_rp1-2*dome,1200.0), dome, wall, seg, z0=0.0), "SIC_RP1")
        write_ascii_stl(RUN/"SIC_Intertank.stl", tube(R, wall*1.5, inter_h, seg, z0=l_rp1), "SIC_INTER")
        write_ascii_stl(RUN/"SIC_LOX_tank.stl", make_tank(Rt, max(l_lox-2*dome,1200.0), dome, wall, seg, z0=l_rp1+inter_h), "SIC_LOX")
        write_ascii_stl(RUN/"SIC_Aft_skirt.stl", tube(R*0.95, wall*3.0, 1600.0, seg, z0=-1600.0), "SIC_AFT_SKIRT")
        write_ascii_stl(RUN/"SIC_Thrust_ring.stl", tube(R*0.82, wall*4.0, 300.0, seg, z0=-300.0), "SIC_THRUST_RING")
        write_ascii_stl(RUN/"SIC_Thrust_beam_A.stl", box(R*1.6, 600.0, 120.0, z0=-600.0, cx=0.0, cy=0.0), "SIC_THRUST_BEAM_A")
        write_ascii_stl(RUN/"SIC_Thrust_beam_B.stl", box(600.0, R*1.6, 120.0, z0=-750.0, cx=0.0, cy=0.0), "SIC_THRUST_BEAM_B")
        write_ascii_stl(RUN/"SIC_Engine_mount_ring.stl", tube(R*0.70, wall*5.0, 250.0, seg, z0=-550.0), "SIC_ENG_MOUNT_RING")
        write_ascii_stl(RUN/"SIC_LOX_downcomer.stl", cylinder(600.0, 10.0, l_rp1+inter_h, 0.0), "SIC_LOX_DOWNCOMER")
        write_ascii_stl(RUN/"SIC_RP1_manifold.stl", cylinder(500.0, 10.0, 1200.0, -1200.0), "SIC_RP1_MANIFOLD")
        for nm,cx,cy in [("A",R,0.0),("B",-R,0.0),("C",0.0,R),("D",0.0,-R)]:
            write_ascii_stl(RUN/(f"SIC_Fin_{nm}.stl"), box(900.0,1600.0,120.0,z0=-600.0,cx=cx,cy=cy), f"SIC_FIN_{nm}")
        offs=[(-2500,0,0),(2500,0,0),(0,0,0),(-1250,-2165,0),(1250,2165,0)]
        for i,(dx,dy,_) in enumerate(offs):
            noz = cone(1200.0, 1800.0, 3200.0, 96, z0=-300.0)
            write_ascii_stl(RUN/(f"F1_nozzle_{i}.stl"), [((a[0]+dx,a[1]+dy,a[2]),(b[0]+dx,b[1]+dy,b[2]),(c[0]+dx,c[1]+dy,c[2])) for (a,b,c) in noz], f"F1_NOZZLE_{i}")
            chamb = cylinder(900.0, 12.0, 800.0, -1100.0)
            write_ascii_stl(RUN/(f"F1_chamber_{i}.stl"), [((a[0]+dx,a[1]+dy,a[2]),(b[0]+dx,b[1]+dy,b[2]),(c[0]+dx,c[1]+dy,c[2])) for (a,b,c) in chamb], f"F1_CHAMBER_{i}")
            tp = cylinder(1200.0, 10.0, 900.0, -2200.0)
            write_ascii_stl(RUN/(f"F1_turbopump_{i}.stl"), [((a[0]+dx,a[1]+dy,a[2]),(b[0]+dx,b[1]+dy,b[2]),(c[0]+dx,c[1]+dy,c[2])) for (a,b,c) in tp], f"F1_TP_{i}")

    elif stage=="S-II":
        l_lox = L*0.22; l_lh2 = L*0.73
        Rt = R*0.90; dome = Rt*0.50
        write_ascii_stl(RUN/"SII_LH2_tank.stl", make_tank(Rt*0.98, max(l_lh2-2*dome, 1800.0), dome, wall, seg, z0=0.0), "SII_LH2")
        z_cb = l_lh2
        write_ascii_stl(RUN/"SII_CB_up.stl",   lathe_solid([(z_cb, Rt),(z_cb+140.0, Rt*0.60)], wall, seg), "SII_CB_UP")
        write_ascii_stl(RUN/"SII_CB_insul.stl",lathe_solid([(z_cb+140.0, Rt*0.60),(z_cb+220.0, Rt*0.60)], wall, seg), "SII_CB_INSUL")
        write_ascii_stl(RUN/"SII_CB_dn.stl",   lathe_solid([(z_cb+220.0, Rt*0.60),(z_cb+360.0, Rt)], wall, seg), "SII_CB_DN")
        write_ascii_stl(RUN/"SII_LOX_tank.stl", make_tank(Rt, max(l_lox-2*dome, 900.0), dome, wall, seg, z0=z_cb+360.0), "SII_LOX")
        write_ascii_stl(RUN/"SII_Aft_skirt.stl",   tube(R*0.95, wall*3.0, 1200.0, seg, z0=-1200.0), "SII_AFT_SKIRT")
        write_ascii_stl(RUN/"SII_Fwd_skirt.stl",   tube(R*0.97, wall*2.5,  900.0, seg, z0=L),       "SII_FWD_SKIRT")
        write_ascii_stl(RUN/"SII_Thrust_ring.stl", tube(R*0.70, wall*4.0, 260.0, seg, z0=-480.0),  "SII_THRUST_RING")
        write_ascii_stl(RUN/"SII_Thrust_beam_A.stl", box(R*1.4, 520.0, 110.0, z0=-700.0, cx=0.0, cy=0.0), "SII_THRUST_BEAM_A")
        write_ascii_stl(RUN/"SII_Thrust_beam_B.stl", box(520.0, R*1.4, 110.0, z0=-820.0, cx=0.0, cy=0.0), "SII_THRUST_BEAM_B")
        write_ascii_stl(RUN/"SII_Engine_mount_ring.stl", tube(R*0.58, wall*5.0, 220.0, seg, z0=-560.0), "SII_ENG_MOUNT_RING")
        write_ascii_stl(RUN/"SII_LOX_manifold.stl", cylinder(420.0, 10.0, 1000.0, -1000.0), "SII_LOX_MANIFOLD")
        write_ascii_stl(RUN/"SII_LH2_return.stl",   cylinder(380.0, 10.0, 1000.0, -1000.0), "SII_LH2_RETURN")
        offs=[(-1800,0,0),(1800,0,0),(0,0,0),(-900,-1550,0),(900,1550,0)]
        for i,(dx,dy,_) in enumerate(offs):
            noz = cone(1050.0, 1550.0, 2400.0, 96, z0=-260.0)
            write_ascii_stl(RUN/(f"J2_nozzle_{i}.stl"), [((a[0]+dx,a[1]+dy,a[2]),(b[0]+dx,b[1]+dy,b[2]),(c[0]+dx,c[1]+dy,c[2])) for (a,b,c) in noz], f"J2_NOZZLE_{i}")
            chamb = cylinder(820.0, 10.0, 700.0, -900.0)
            write_ascii_stl(RUN/(f"J2_chamber_{i}.stl"), [((a[0]+dx,a[1]+dy,a[2]),(b[0]+dx,b[1]+dy,b[2]),(c[0]+dx,c[1]+dy,c[2])) for (a,b,c) in chamb], f"J2_CHAMBER_{i}")
            tp = cylinder(1000.0, 10.0, 700.0, -1650.0)
            write_ascii_stl(RUN/(f"J2_turbopump_{i}.stl"), [((a[0]+dx,a[1]+dy,a[2]),(b[0]+dx,b[1]+dy,b[2]),(c[0]+dx,c[1]+dy,c[2])) for (a,b,c) in tp], f"J2_TP_{i}")

    elif stage=="S-IVB":
        # S-IVB: 상단 LOX, 하단 LH2, IU 링, APS, 단순 배플, J-2 1기
        l_lox = L*0.26; l_lh2 = L*0.69
        Rt = R*0.90; dome = Rt*0.48
        # LH2(하)
        write_ascii_stl(RUN/"SIVB_LH2_tank.stl", make_tank(Rt*0.98, max(l_lh2-2*dome, 1400.0), dome, wall, seg, z0=0.0), "SIVB_LH2")
        # LH2 배플 두 장(간단 디스크)
        z_lh2 = 0.0 + dome + max(l_lh2-2*dome,1400.0)*0.33
        z_lh2b= 0.0 + dome + max(l_lh2-2*dome,1400.0)*0.66
        write_ascii_stl(RUN/"SIVB_LH2_baffle_0.stl", lathe_solid([(z_lh2, Rt*0.85),(z_lh2+40.0, Rt*0.30)], wall, seg), "SIVB_LH2_BAFFLE_0")
        write_ascii_stl(RUN/"SIVB_LH2_baffle_1.stl", lathe_solid([(z_lh2b, Rt*0.85),(z_lh2b+40.0, Rt*0.30)], wall, seg), "SIVB_LH2_BAFFLE_1")
        # LOX(상)
        write_ascii_stl(RUN/"SIVB_LOX_tank.stl", make_tank(Rt, max(l_lox-2*dome, 700.0), dome, wall, seg, z0=L-l_lox), "SIVB_LOX")
        # 상부 IU 링 + 상부 스커트
        write_ascii_stl(RUN/"SIVB_IU_ring.stl",  tube(R*0.96, wall*3.0, 500.0, seg, z0=L), "SIVB_IU_RING")
        write_ascii_stl(RUN/"SIVB_Fwd_skirt.stl",tube(R*0.97, wall*2.5, 600.0, seg, z0=L+500.0), "SIVB_FWD_SKIRT")
        # 하부 스커트 + 추력구조
        write_ascii_stl(RUN/"SIVB_Aft_skirt.stl",   tube(R*0.95, wall*3.0, 900.0, seg, z0=-900.0), "SIVB_AFT_SKIRT")
        write_ascii_stl(RUN/"SIVB_Thrust_ring.stl", tube(R*0.72, wall*4.0, 240.0, seg, z0=-360.0), "SIVB_THRUST_RING")
        write_ascii_stl(RUN/"SIVB_Engine_mount_ring.stl", tube(R*0.60, wall*5.0, 220.0, seg, z0=-520.0), "SIVB_ENG_MOUNT_RING")
        # 배관
        write_ascii_stl(RUN/"SIVB_LOX_downcomer.stl", cylinder(380.0, 10.0, L-(L-l_lox), L-l_lox-1200.0), "SIVB_LOX_DOWNCOMER")
        write_ascii_stl(RUN/"SIVB_LH2_return.stl",    cylinder(340.0, 10.0, 1000.0, -1000.0), "SIVB_LH2_RETURN")
        # APS 포드(좌우)
        aps_r = R*0.85
        write_ascii_stl(RUN/"SIVB_APS_L.stl", box(600.0, 400.0, 300.0, z0=-400.0, cx= aps_r, cy=0.0), "SIVB_APS_L")
        write_ascii_stl(RUN/"SIVB_APS_R.stl", box(600.0, 400.0, 300.0, z0=-400.0, cx=-aps_r, cy=0.0), "SIVB_APS_R")
        # J-2 1기
        noz = cone(1050.0, 1550.0, 2400.0, 96, z0=-260.0)
        write_ascii_stl(RUN/"J2_nozzle.stl", noz, "J2_NOZZLE")
        chamb = cylinder(820.0, 10.0, 700.0, -900.0)
        write_ascii_stl(RUN/"J2_chamber.stl", chamb, "J2_CHAMBER")
        tp = cylinder(1000.0, 10.0, 700.0, -1650.0)
        write_ascii_stl(RUN/"J2_turbopump.stl", tp, "J2_TP")

    meta={"ok":True,"stage":stage,"run_rel":str(RUN.relative_to(DATA)).replace("\\","/"),
          "parts":[x.name for x in sorted(RUN.iterdir()) if x.suffix.lower()==".stl"]}
    (RUN/"meta.json").write_text(json.dumps(meta,indent=2),encoding="utf-8")
    return meta
