from __future__ import annotations
from fastapi import APIRouter, Body
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import numpy as np, os, json, datetime, trimesh as tm, math

RUNS_DIR = os.path.join("data","geometry","cad","j58_v23_runs")
os.makedirs(RUNS_DIR, exist_ok=True)

CLR = 0.15
SECTIONS = int(os.getenv("J58_SECTIONS", "64"))
TRIMESH_PROCESS = os.getenv("J58_PROCESS", "0") == "1"

def tube(r_in, r_out, h, z0=0.0, sections=SECTIONS):
    ang=np.linspace(0,2*np.pi,sections,endpoint=False); c,s=np.cos(ang),np.sin(ang)
    ob=np.column_stack([r_out*c,r_out*s,np.full_like(c,z0)])
    ot=np.column_stack([r_out*c,r_out*s,np.full_like(c,z0+h)])
    ib=np.column_stack([r_in*c, r_in*s, np.full_like(c,z0)])
    it=np.column_stack([r_in*c, r_in*s, np.full_like(c,z0+h)])
    V=np.vstack([ob,ot,ib,it]); n=len(ang); F=[]
    q=lambda a,b,c,d:[[a,b,c],[a,c,d]]
    for i in range(n):
        j=(i+1)%n
        F+=q(i,j,n+j,n+i); F+=q(2*n+i,3*n+i,3*n+j,2*n+j); F+=q(i,2*n+j,2*n+i,j); F+=q(n+i,3*n+i,3*n+j,n+j)
    return tm.Trimesh(vertices=V, faces=np.asarray(F), process=TRIMESH_PROCESS)

def frustum(r0,r1,h,z0=0.0,sections=SECTIONS,cap=True):
    ang=np.linspace(0,2*np.pi,sections,endpoint=False)
    c,s=np.cos(ang),np.sin(ang)
    vb=np.column_stack([r0*c,r0*s,np.full_like(c,z0)])
    vt=np.column_stack([r1*c,r1*s,np.full_like(c,z0+h)])
    V=np.vstack([vb,vt]); n=len(ang); F=[]
    for i in range(n):
        j=(i+1)%n; a,b=i,j; cc=n+j; d=n+i; F+=[[a,b,cc],[a,cc,d]]
    if cap and r0>1e-6:
        cb=len(V); V=np.vstack([V,[0,0,z0]])
        for i in range(n): F.append([cb,(i+1)%n,i])
    if cap and r1>1e-6:
        ct=len(V); V=np.vstack([V,[0,0,z0+h]])
        for i in range(n): F.append([ct,n+i,n+((i+1)%n)])
    return tm.Trimesh(vertices=V, faces=np.asarray(F), process=TRIMESH_PROCESS)

def cyl(r,h,z0=0.0,sections=SECTIONS):
    m=tm.creation.cylinder(radius=r,height=h,sections=sections); m.apply_translation([0,0,z0+h*0.5])
    if not TRIMESH_PROCESS: m.process(False)
    return m

def cone(r0,r1,h,z0=0.0,sections=SECTIONS):
    if hasattr(tm.creation,"conical_frustum"):
        m=tm.creation.conical_frustum(radius_top=r1,radius_bottom=r0,height=h,sections=sections)
        m.apply_translation([0,0,z0+h*0.5]); 
        if not TRIMESH_PROCESS: m.process(False)
        return m
    return frustum(r0,r1,h,z0=z0,sections=sections,cap=True)

def rotZ(m,deg):
    m2=m.copy(); m2.apply_transform(tm.transformations.rotation_matrix(np.deg2rad(deg),[0,0,1])); return m2

def blade_ring(n,r_root,r_tip,thick,z0,twist_deg,hub_r_in,hub_r_out):
    hub=tube(hub_r_in,hub_r_out,thick,z0); parts=[hub]
    b_w,b_t,b_h=(r_tip-r_root)*0.22,thick*1.2,(r_tip-r_root)*0.9
    for k in range(n):
        ang=2*np.pi*k/n
        b=tm.creation.box(extents=[b_w,b_t,b_h])
        b.apply_translation([r_root+(r_tip-r_root)*0.55,0,z0+thick*0.5])
        b.apply_transform(tm.transformations.rotation_matrix(np.deg2rad(twist_deg),[0,0,1]))
        b.apply_transform(tm.transformations.rotation_matrix(ang,[0,0,1]))
        parts.append(b)
    return tm.util.concatenate(parts)

def stator_ring(n,r_root,r_tip,thick,z0,twist_deg):
    ring=tube(r_root,r_tip,thick,z0); parts=[ring]
    b_w,b_t,b_h=(r_tip-r_root)*0.18,thick*1.1,(r_tip-r_root)*0.7
    for k in range(n):
        ang=2*np.pi*k/n
        b=tm.creation.box(extents=[b_w,b_t,b_h])
        b.apply_translation([r_root+(r_tip-r_root)*0.5,0,z0+thick*0.5])
        b.apply_transform(tm.transformations.rotation_matrix(np.deg2rad(twist_deg),[0,0,1]))
        b.apply_transform(tm.transformations.rotation_matrix(ang,[0,0,1]))
        parts.append(b)
    return tm.util.concatenate(parts)

def seat_ring(r0,r1,th,z0): return tube(r0,r1,th,z0)

# shaft: 전방 클리어 + 후방 오버행
def shaft_main(L, front_clear_frac=0.08, rear_overhang=6.0):
    z0 = max(0.0, L*front_clear_frac)
    length = (L - z0) + rear_overhang
    return cyl(2.5-0.05, length, z0)

def bearing_holder(od=16.0,id=5.0,w=5.0,wall=4.0,z0=0.0):
    rin=(od/2.0)+CLR; rout=rin+wall; return tube(rin,rout,w+1.0,z0)
def bearing_rail(r_in,h,z0):
    rout=r_in-0.6; rin=rout-2.5; return tube(rin,rout,h,z0)
def spacer_5mm(th,od,z0): return tube(2.5+0.05, od/2.0, th, z0)

class J58V23Param(BaseModel):
    L_total: float=300.0; R_casing: float=30.0
    N_fan:int=12; N_comp:int=14; N_turb:int=16; eps:float=12.0
    build_both_sides: bool=True

def _engine_parts(p:J58V23Param, tag:str):
    L,R=p.L_total,p.R_casing
    GAP=max(0.3,0.003*L)
    R_IN=0.97*R-CLR
    cap=lambda r:min(r,R_IN)
    parts=[]; z=0.0
    Ls=L*0.12; parts.append((f"inlet_spike_{tag}.stl", cone(cap(0.01*R), cap(0.34*R), Ls, z))); z+=Ls*0.9+GAP
    th=L*0.02; Hrs=th
    parts.append((f"fan_rotor_{tag}.stl",  blade_ring(p.N_fan, cap(0.25*R),cap(0.95*R), Hrs, z, 16, 2.55,8.0)));  z+=Hrs*1.1+GAP
    parts.append((f"fan_stator_{tag}.stl", stator_ring(p.N_fan,cap(0.30*R),cap(0.96*R), Hrs*0.8, z,-12)));       z+=Hrs+GAP
    parts.append((f"seat_fan_{tag}.stl",   seat_ring(cap(0.25*R),cap(0.27*R), Hrs*0.35, z)));                    z+=Hrs*0.4+GAP
    parts.append((f"comp_rotor_{tag}.stl", blade_ring(p.N_comp,cap(0.20*R),cap(0.92*R), Hrs, z, 22, 2.55,7.5))); z+=Hrs*1.1+GAP
    parts.append((f"comp_stator_{tag}.stl",stator_ring(p.N_comp,cap(0.26*R),cap(0.93*R), Hrs*0.8, z,-14)));      z+=Hrs+GAP
    parts.append((f"seat_comp_{tag}.stl",  seat_ring(cap(0.22*R),cap(0.24*R), Hrs*0.35, z)));                    z+=Hrs*0.4+GAP
    Lc=L*0.20; parts.append((f"combustor_shell_{tag}.stl", tube(cap(0.65*R),cap(0.95*R), Lc, z)));               z+=Lc+GAP
    parts.append((f"turb_rotor_{tag}.stl", blade_ring(p.N_turb,cap(0.22*R),cap(0.88*R), Hrs, z, 18, 2.55,7.5))); z+=Hrs*1.1+GAP
    parts.append((f"turb_stator_{tag}.stl",stator_ring(p.N_turb,cap(0.28*R),cap(0.89*R), Hrs*0.8, z,-10)));      z+=Hrs+GAP
    parts.append((f"seat_turb_{tag}.stl",  seat_ring(cap(0.24*R),cap(0.26*R), Hrs*0.35, z)));                    z+=Hrs*0.4+GAP
    Lab=L*0.18; parts.append((f"afterburner_shell_{tag}.stl", tube(cap(0.88*R),cap(0.98*R), Lab, z)));           z+=Lab+GAP
    Ln=min(L*0.18,0.16*L); r_th=cap(0.35*R); A_th=math.pi*(r_th**2); r_ex=min(math.sqrt(max(1e-9,p.eps*A_th/math.pi)),R_IN)
    parts.append((f"nozzle_cone_{tag}.stl", cone(r_th, r_ex, Ln, z)));                                           z+=Ln+GAP
    parts.append((f"casing_front_{tag}.stl", tube(R_IN,R,0.33*L,0.0)))
    parts.append((f"casing_mid_{tag}.stl",   tube(R_IN,R,0.34*L,0.33*L)))
    parts.append((f"casing_aft_{tag}.stl",   tube(R_IN,R,0.33*L,0.67*L)))
    parts.append((f"splice_front_mid_{tag}.stl", tube(R-1.8,R-0.8,3.0,0.33*L-1.5)))
    parts.append((f"splice_mid_aft_{tag}.stl",   tube(R-1.8,R-0.8,3.0,0.67*L-1.5)))
    parts.append((f"shaft_main_{tag}.stl", shaft_main(L, front_clear_frac=0.08, rear_overhang=6.0)))
    sp_th = Hrs*0.6; sp_od = 16.0; z_sp = 0.05*L + Hrs*0.6
    for i in range(1,7): parts.append((f"spacer_{i}_{tag}.stl", spacer_5mm(sp_th, sp_od, z_sp))); z_sp += sp_th*1.2
    parts.append((f"bearing_holder_L_{tag}.stl", bearing_holder(od=16, id=5, w=5, wall=4, z0=0.07*L)))
    parts.append((f"bearing_holder_R_{tag}.stl", bearing_holder(od=16, id=5, w=5, wall=4, z0=0.93*L)))
    parts.append((f"bearing_rail_L_{tag}.stl",   bearing_rail(0.97*R-CLR, h=6, z0=0.065*L)))
    parts.append((f"bearing_rail_R_{tag}.stl",   bearing_rail(0.97*R-CLR, h=6, z0=0.925*L)))
    return parts

def base_rail(CC,L,y0,rail_w,rail_h):
    seg=[]
    for x in (-CC*0.5,+CC*0.5):
        b=tm.creation.box(extents=[rail_w,rail_h,L*1.05]); b.apply_translation([x,y0,L*0.525]); seg.append(b)
    for zf in (0.18*L,0.78*L):
        c=tm.creation.box(extents=[CC+rail_w,rail_h,rail_w]); c.apply_translation([0,y0,zf]); seg.append(c)
    return tm.util.concatenate(seg)

def motor130(yc,zc):
    base=tm.creation.box(extents=[28,22,3]); base.apply_translation([0,0,zc+1.5])
    body=tm.creation.box(extents=[28,22,16]); body.apply_translation([0,0,zc+3+8])
    m=tm.util.concatenate([base,body]); m.apply_translation([-14,-11,yc]); return m

def pulley_disc(r,w,x,y,zc): p=cyl(r,w,zc-w*0.5); p.apply_translation([x,y,0.0]); return p
def rotZ(m,deg): m2=m.copy(); m2.apply_transform(tm.transformations.rotation_matrix(np.deg2rad(deg),[0,0,1])); return m2
def belt_bar_xy(x0,y0,x1,y1,zc,thick,width):
    dx,dy=(x1-x0),(y1-y0); L=math.hypot(dx,dy); b=tm.creation.box(extents=[L,thick,width])
    b.apply_translation([L*0.5,0,zc]); ang=math.degrees(math.atan2(dy,dx)); b=rotZ(b,ang); b.apply_translation([x0,y0,0]); return b

class BuildParam(BaseModel):
    L_total: float=300.0; R_casing: float=30.0
    N_fan:int=12; N_comp:int=14; N_turb:int=16; eps:float=12.0
    both_sides: bool=True; twin_layout: bool=True; engine_cc: float=120.0
    pylon_enable: bool=False
    ribs_enable: bool=True; ribs_count: int=6
    base_enable: bool=True
    base_drop: float=36.0; rail_w: float=12.0; rail_h: float=6.0
    cradles_enable: bool=True
    motor_drop: float=48.0; drive_z_frac: float=0.18
    pulley_r_engine: float=8.0; pulley_r_motor: float=10.0
    belt_width: float=6.0; belt_thick: float=1.6

api=APIRouter(prefix="/wb")

def build_run(p:BuildParam)->dict:
    run="run-"+datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir=os.path.join(RUNS_DIR,run); os.makedirs(out_dir,exist_ok=True)

    eng=J58V23Param(L_total=p.L_total,R_casing=p.R_casing,N_fan=p.N_fan,N_comp=p.N_comp,N_turb=p.N_turb,eps=p.eps,build_both_sides=p.both_sides)
    tags=["R","L"] if eng.build_both_sides else ["R"]

    bom=[]; sc=tm.Scene()
    for tag in tags:
        parts=_engine_parts(eng,tag)
        xoff=(+p.engine_cc*0.5 if tag=="R" else -p.engine_cc*0.5) if (p.twin_layout and eng.build_both_sides) else 0.0
        for name,m in parts:
            m.apply_translation([xoff,0.0,0.0])
            path=os.path.join(out_dir,name); m.export(path); bom.append({"name":name,"path":path}); sc.add_geometry(m)

        if p.ribs_enable:
            R_in=0.97*p.R_casing-CLR; zlist=np.linspace(0.1*p.L_total, 0.9*p.L_total, p.ribs_count)
            for i,zz in enumerate(zlist):
                rib=tube(R_in-3.0, R_in-0.8, 2.2, zz-1.1)
                rib.apply_translation([xoff,0,0]); nm=f"rib_{i+1}_{tag}.stl"
                path=os.path.join(out_dir,nm); rib.export(path); bom.append({"name":nm[:-4],"path":path}); sc.add_geometry(rib)

    if p.base_enable and eng.build_both_sides and p.twin_layout:
        y_base=-p.base_drop; base=base_rail(p.engine_cc,p.L_total,y_base,p.rail_w,p.rail_h); sc.add_geometry(base)
        base.export(os.path.join(out_dir,"base_frame.stl")); bom.append({"name":"base_frame","path":os.path.join(out_dir,"base_frame.stl")})
        y_motor=-p.motor_drop; z_drive=p.drive_z_frac*p.L_total
        m130=motor130(y_motor,z_drive-8.0); sc.add_geometry(m130)
        m130.export(os.path.join(out_dir,"starter_motor_130.stl")); bom.append({"name":"starter_motor_130","path":os.path.join(out_dir,"starter_motor_130.stl")})
        for nm,mesh in [("pulley_motor.stl",pulley_disc(p.pulley_r_motor,p.belt_width,0.0,y_motor,z_drive)),
                        ("pulley_engine_L.stl",pulley_disc(p.pulley_r_engine,p.belt_width,-p.engine_cc*0.5,0.0,z_drive)),
                        ("pulley_engine_R.stl",pulley_disc(p.pulley_r_engine,p.belt_width,+p.engine_cc*0.5,0.0,z_drive))]:
            sc.add_geometry(mesh); mesh.export(os.path.join(out_dir,nm)); bom.append({"name":nm[:-4],"path":os.path.join(out_dir,nm)})
        for nm,mesh in [("belt_L_stub.stl",belt_bar_xy(0.0,y_motor,-p.engine_cc*0.5,0.0,z_drive,p.belt_thick,p.belt_width)),
                        ("belt_R_stub.stl",belt_bar_xy(0.0,y_motor,+p.engine_cc*0.5,0.0,z_drive,p.belt_thick,p.belt_width))]:
            sc.add_geometry(mesh); mesh.export(os.path.join(out_dir,nm)); bom.append({"name":nm[:-4],"path":os.path.join(out_dir,nm)})

    glb=os.path.join(out_dir,"j58_v23_assembly.glb"); sc.export(glb)
    meta={"params":p.model_dump(),"parts":bom,"glb":glb,"out_dir":out_dir}
    with open(os.path.join(out_dir,"j58_v23_bom.json"),"w",encoding="utf-8") as f: json.dump(meta,f,ensure_ascii=False,indent=2)
    with open(os.path.join(RUNS_DIR,"_last.json"),"w",encoding="utf-8") as f: json.dump(meta,f,ensure_ascii=False,indent=2)
    return {"ok":True,**meta}

def _safe(rel:str):
    base=os.path.abspath("data"); p=os.path.abspath(os.path.join(base,rel.replace("/",os.sep)))
    return p if p.startswith(base) else None

@api.post("/cad/j58_v23")
def j58_v23_build(p:BuildParam=Body(BuildParam())): return build_run(p)
@api.get("/cad/j58_v23_demo")
def j58_v23_demo(): return build_run(BuildParam())
@api.get("/files/{rel_path:path}")
def send_file(rel_path:str):
    full=_safe(rel_path)
    if not full or not os.path.exists(full): return JSONResponse({"ok":False,"reason":"not_found","rel":rel_path},status_code=404)
    return FileResponse(full)
