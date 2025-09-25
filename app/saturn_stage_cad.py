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

# ---------- STL ----------
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

# ---------- Primitives ----------
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

def ring_disk(R_in, R_out, H, seg=128, z0=0.0):
    wall = R_out-R_in
    return lathe_solid([(z0,R_out),(z0+H,R_out)], wall, seg)

def bell_profile(Rt, Re, L, theta_n=30.0, theta_e=7.0, n=64, z0=0.0):
    tn=math.tan(math.radians(theta_n)); te=math.tan(math.radians(theta_e))
    p0=(z0,Rt); p3=(z0+L,Re)
    p1=(z0+L/3.0, Rt + (L/3.0)*tn)
    p2=(z0+2*L/3.0, Re - (L/3.0)*te)
    pts=[]
    for i in range(n+1):
        t=i/n; u=1-t
        z=(u**3*p0[0] + 3*u*u*t*p1[0] + 3*u*t*t*p2[0] + t**3*p3[0])
        r=(u**3*p0[1] + 3*u*u*t*p1[1] + 3*u*t*t*p2[1] + t**3*p3[1])
        pts.append((z,r))
    return pts

def make_bell(Rt, Re, L, wall, seg=128, z0=0.0):
    return lathe_solid(bell_profile(Rt,Re,L,z0=z0), wall, seg)

def elbow_90(Rc, r_out, wall, seg_phi=24, seg_theta=24, z0=0.0):
    # 90° 토러스 섹션(평면 XY, +X→+Y로 굽힘). 중심은 원점, z는 z0 부근.
    r_in=max(r_out-wall, 0.001)
    verts=[]; faces=[]
    def ring(r):
        vv=[]
        for i in range(seg_phi+1):
            phi=(math.pi/2)*i/seg_phi
            for j in range(seg_theta):
                th=2*math.pi*j/seg_theta
                x=(Rc + r*math.cos(th))*math.cos(phi)
                y=(Rc + r*math.cos(th))*math.sin(phi)
                z=z0 + r*math.sin(th)
                vv.append((x,y,z))
        return vv
    vo=ring(r_out); vi=ring(r_in)
    verts=vo+vi
    # 외피/내피
    def idx(i,j,seg_theta): return i*seg_theta + j
    for i in range(seg_phi):
        for j in range(seg_theta):
            j2=(j+1)%seg_theta
            a=idx(i,j,seg_theta); b=idx(i+1,j,seg_theta); c=idx(i+1,j2,seg_theta); d=idx(i,j2,seg_theta)
            # outer
            faces+=[(a,d,c),(a,c,b)]
            # inner (반전)
            off=len(vo)
            a2=off+a; b2=off+b; c2=off+c; d2=off+d
            faces+=[(a2,c2,d2),(a2,b2,c2)]
    # 양 끝 캡
    for j in range(seg_theta):
        j2=(j+1)%seg_theta
        # phi=0 면
        a=idx(0,j,seg_theta); d=idx(0,j2,seg_theta)
        ai=len(vo)+idx(0,j,seg_theta); di=len(vo)+idx(0,j2,seg_theta)
        faces+=[(ai,d,a),(ai,di,d)]
        # phi=pi/2 면
        b=idx(seg_phi,j,seg_theta); c=idx(seg_phi,j2,seg_theta)
        bi=len(vo)+idx(seg_phi,j,seg_theta); ci=len(vo)+idx(seg_phi,j2,seg_theta)
        faces+=[(b,ci,bi),(b,c,ci)]
    return verts,faces

def box(x0,x1,y0,y1,z0,z1):
    v=[(x0,y0,z0),(x1,y0,z0),(x1,y1,z0),(x0,y1,z0),(x0,y0,z1),(x1,y0,z1),(x1,y1,z1),(x0,y1,z1)]
    f=[(0,1,2),(0,2,3),(4,5,6),(4,6,7),(0,1,5),(0,5,4),(1,2,6),(1,6,5),(2,3,7),(2,7,6),(3,0,4),(3,4,7)]
    return v,f

# ---------- Tanks ----------
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

def make_common_bulkhead(R, dome_h, wall, gap=30.0, seg=128, z_mid=0.0):
    # 위·아래 돔을 등간격으로 맞대고 사이에 단열층(gap) 별도 파트
    # 위돔: z_mid..z_mid+dome_h, 아래돔: z_mid-gap..z_mid-gap-dome_h
    # 돔 자체는 얇은 셸
    up_prof=[(z_mid, R)]
    for i in range(18):
        t=i/17; z=z_mid + dome_h*t; r=(R**2 - (R-dome_h*t)**2)**0.5
        up_prof.append((z,r))
    dn_prof=[]
    for i in range(18):
        t=i/17; z=z_mid-gap - dome_h*t; r=(R**2 - (R-dome_h*t)**2)**0.5
        dn_prof.append((z,r))
    v1,f1=lathe_solid(up_prof, wall, seg)
    v2,f2=lathe_solid(dn_prof, wall, seg)
    # 단열층: 얇은 링 디스크
    v3,f3=ring_disk(R*0.98, R, gap, seg, z_mid-gap)
    return (v1,f1),(v2,f2),(v3,f3)

# ---------- Engines L2 ----------
def f1_parts(wall=2.0, seg=128, z0=-5800.0):
    Re=1850.0; L=5800.0; Rt=Re/4.0
    out=[]
    v,f = make_bell(Rt,Re,L,wall,seg,z0); out.append(("F1_nozzle.stl",v,f))
    v,f = tube(Rt*1.25, wall*3, 320.0, seg, z0+L); out.append(("F1_chamber.stl",v,f))
    v,f = ring_disk(Re*0.55, Re*0.80, 12.0, seg, z0+L*0.52); out.append(("F1_film_band.stl",v,f))
    v,f = tube(Re*0.48, wall*6, 70.0, seg, z0+L+160.0); out.append(("F1_injector.stl",v,f))
    v,f = ring_disk(Re*0.70, Re*0.95, 16.0, seg, z0-200.0); out.append(("F1_heat_shield.stl",v,f))
    # 짐벌 액추에이터(수직 스트럿 4개)
    r=Re*0.65; dz=260.0; H=280.0; Rs=80.0
    for k,(cx,cy) in enumerate((( r,0),(0, r),(-r,0),(0,-r))):
        v1,f1 = tube(Rs, wall*2, H, seg, z0+L-120.0)
        # 평행이동: 생성 후 좌표 오프셋만
        v1=[(x+cx,y+cy,z) for (x,y,z) in v1]
        out.append((f"F1_gimbal_strut_{k}.stl", v1, f1))
    return out

def j2_parts(wall=2.0, seg=128, z0=-3380.0):
    Re=1015.0; L=3380.0; Rt=Re/(27.5**0.5)
    out=[]
    v,f = make_bell(Rt,Re,L,wall,seg,z0); out.append(("J2_nozzle.stl",v,f))
    v,f = tube(Rt*1.30, wall*3, 240.0, seg, z0+L); out.append(("J2_chamber.stl",v,f))
    v,f = ring_disk(Re*0.60, Re*0.82, 10.0, seg, z0+L*0.55); out.append(("J2_film_band.stl",v,f))
    v,f = tube(Re*0.50, wall*6, 60.0, seg, z0+L+140.0); out.append(("J2_injector.stl",v,f))
    # 터보펌프 하우징 더미(상부 원통)
    v,f = tube(Rt*1.6, wall*3, 260.0, seg, z0+L+240.0); out.append(("J2_turbopump.stl",v,f))
    # 가스제너레이터 배기 덕트 90°
    v,f = elbow_90(Rc=Re*0.9, r_out=160.0, wall=10.0, seg_phi=18, seg_theta=24, z0=z0+L+180.0); out.append(("J2_gg_duct.stl",v,f))
    return out

# ---------- Stage build ----------
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

    # Shell
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
        # Thrust ring
        v,f = tube(Rstage*0.85, wall*4, 800.0, seg, z0=-800.0)
        write_ascii_stl(run/"SIC_Thrust_ring.stl", v, f, "SIC_THRUST")
        # Cross beams(십자 보강)
        for k in (0,1):
            x=Rstage*0.60
            if k==0: v,f=box(-x,x,-200.0,200.0,-720.0,-640.0)
            else:    v,f=box(-200.0,200.0,-x,x,-720.0,-640.0)
            write_ascii_stl(run/f"SIC_Thrust_beam_{k}.stl", v, f, f"SIC_BEAM_{k}")
        # Engine mount ring
        v,f = ring_disk(Rstage*0.40, Rstage*0.62, 40.0, seg, z0=-700.0)
        write_ascii_stl(run/"SIC_Engine_mount_ring.stl", v, f, "SIC_EMR")
        # Fin
        x0=Rstage; x1=Rstage+900.0; y0=-800.0; y1=800.0; z0f=-600.0; z1f=-480.0
        v=[(x0,y0,z0f),(x1,y0,z0f),(x1,y1,z0f),(x0,y1,z0f),(x0,y0,z1f),(x1,y0,z1f),(x1,y1,z1f),(x0,y1,z1f)]
        f=[(0,1,2),(0,2,3),(4,5,6),(4,6,7),(0,1,5),(0,5,4),(1,2,6),(1,6,5),(2,3,7),(2,7,6),(3,0,4),(3,4,7)]
        write_ascii_stl(run/"SIC_Fin_rect.stl", v, f, "SIC_FIN")
        # External LOX feedline: 수직 파이프 + 90° 엘보(셸 바깥 +X)
        pipe_R=380.0; pipe_wall=8.0; xoff=Rstage+pipe_R+120.0
        v,f = tube(pipe_R, pipe_wall, L*0.70, seg, z0=L*0.30)   # vertical
        v=[(x+xoff,y,z) for (x,y,z) in v]; write_ascii_stl(run/"SIC_LOX_pipe_vert.stl", v, f, "SIC_LOX_PIPE_V")
        v,f = elbow_90(Rc=pipe_R*2.2, r_out=pipe_R, wall=pipe_wall, seg_phi=18, seg_theta=24, z0=-400.0)
        v=[(x+xoff,y,z) for (x,y,z) in v]; write_ascii_stl(run/"SIC_LOX_elbow.stl", v, f, "SIC_LOX_ELBOW")
        # Engines(5기, 파츠 묶음)
        for name,v,f in f1_parts(wall,seg,z0=-5800.0):
            write_ascii_stl(run/name, v, f, name[:-4])

    elif stage=="S-II":
        l_lox=L*0.22; l_lh2=L*0.73; Rt=Rstage*0.9; domeL=Rt*0.50
        z_top=L-l_lox
        v,f = make_tank(Rt, max(l_lox-2*domeL,900.0), domeL, wall, seg, z0=z_top)
        write_ascii_stl(run/"SII_LOX_tank.stl", v, f, "SII_LOX")
        # Common bulkhead(이중돔+단열층)
        z_cb = z_top + max(l_lox-2*domeL, 900.0) + domeL*0.5
        (v1,f1),(v2,f2),(v3,f3) = make_common_bulkhead(R=Rt*0.98, dome_h=domeL*0.92, wall=wall, gap=30.0, seg=seg, z_mid=z_cb)
        write_ascii_stl(run/"SII_CB_up.stl", v1, f1, "SII_CB_UP")
        write_ascii_stl(run/"SII_CB_dn.stl", v2, f2, "SII_CB_DN")
        write_ascii_stl(run/"SII_CB_insul.stl", v3, f3, "SII_CB_INS")
        v,f = make_tank(Rt*0.98, max(l_lh2-2*domeL,1800.0), domeL, wall, seg, z0=0.0)
        write_ascii_stl(run/"SII_LH2_tank.stl", v, f, "SII_LH2")
        # Engines(5기, 파츠 묶음)
        for name,v,f in j2_parts(wall,seg,z0=-3380.0):
            write_ascii_stl(run/name, v, f, name[:-4])

    else:  # S-IVB
        Rt=Rstage*0.9; l_lox=L*0.26; l_lh2=L*0.69; domeL=Rt*0.48
        v,f = make_tank(Rt, max(l_lox-2*domeL,700.0), domeL, wall, seg, z0=L-l_lox)
        write_ascii_stl(run/"SIVB_LOX_tank.stl", v, f, "S4B_LOX")
        v,f = make_tank(Rt*0.98, max(l_lh2-2*domeL,1400.0), domeL, wall, seg, z0=0.0)
        write_ascii_stl(run/"SIVB_LH2_tank.stl", v, f, "S4B_LH2")
        # LH2 내부 배플 2장
        for i,zz in enumerate((l_lh2*0.35, l_lh2*0.65)):
            v,f = ring_disk(Rt*0.10, Rt*0.95, 8.0, seg, z0=zz)
            write_ascii_stl(run/f"SIVB_LH2_baffle_{i}.stl", v, f, f"S4B_BAFFLE_{i}")
        # IU(Instrument Unit) 링(상단)
        v,f = ring_disk(R_in=Rstage*0.70, R_out=Rstage*0.95, H=250.0, seg=seg, z0=L+200.0)
        write_ascii_stl(run/"SIVB_IU_ring.stl", v, f, "S4B_IU")
        # Single J-2
        for name,v,f in j2_parts(wall,seg,z0=-3380.0):
            write_ascii_stl(run/name, v, f, name[:-4])

    meta={"ok":True,"stage":stage,"run_rel":str(run.relative_to(DATA)).replace("\\","/"),
          "parts":[x.name for x in sorted(run.iterdir()) if x.suffix.lower()==".stl"]}
    (run/"meta.json").write_text(json.dumps(meta,indent=2),encoding="utf-8")
    return meta
