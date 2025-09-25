from __future__ import annotations
from fastapi import APIRouter, Body
from pathlib import Path
from datetime import datetime
import math, json, struct

api = APIRouter(prefix="/wb", tags=["j58"])
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

def tube(R_out, wall, H, seg=128, z0=0.0):
    return lathe_solid([(z0,R_out),(z0+H,R_out)], wall, seg)

def ring_disk(R_in, R_out, H, seg=128, z0=0.0):
    wall=R_out-R_in
    return lathe_solid([(z0,R_out),(z0+H,R_out)], wall, seg)

def nozzle_cd(R_inlet, R_throat, R_exit, Lc, Ld, wall, seg=128, z0=0.0):
    prof=[(z0, R_inlet),(z0+Lc, R_throat),(z0+Lc+Ld, R_exit)]
    return lathe_solid(prof, wall, seg)

def elbow_90(Rc, r_out, wall, seg_phi=24, seg_theta=24, z0=0.0):
    r_in=max(r_out-wall, 0.001)
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
    vo=ring(r_out); vi=ring(r_in); verts=vo+vi; faces=[]
    def idx(i,j): return i*seg_theta + j
    for i in range(seg_phi):
        for j in range(seg_theta):
            j2=(j+1)%seg_theta
            a=idx(i,j); b=idx(i+1,j); c=idx(i+1,j2); d=idx(i,j2)
            faces+=[(a,d,c),(a,c,b)]
            off=len(vo); a2=off+a; b2=off+b; c2=off+c; d2=off+d
            faces+=[(a2,c2,d2),(a2,b2,c2)]
    for j in range(seg_theta):
        j2=(j+1)%seg_theta
        a=idx(0,j); d=idx(0,j2); ai=len(vo)+idx(0,j); di=len(vo)+idx(0,j2)
        faces+=[(ai,d,a),(ai,di,d)]
        b=idx(seg_phi,j); c=idx(seg_phi,j2); bi=len(vo)+idx(seg_phi,j); ci=len(vo)+idx(seg_phi,j2)
        faces+=[(b,ci,bi),(b,c,ci)]
    return verts,faces

def pack_glb(meshes):
    buffers=[]; bufferViews=[]; accessors=[]; nodes=[]; gltf_meshes=[]; bin_blob=b""
    for m in meshes:
        start=len(bin_blob); pf=[c for v in m["positions"] for c in v]
        bin_blob += struct.pack("<%sf"%len(pf), *pf)
        if len(bin_blob)%4: bin_blob += b"\x00"*(4-len(bin_blob)%4)
        bufferViews.append({"buffer":0,"byteOffset":start,"byteLength":len(bin_blob)-start})
        cnt=len(m["positions"]); minv=[min(v[i] for v in m["positions"]) for i in range(3)]
        maxv=[max(v[i] for v in m["positions"]) for i in range(3)]
        accessors.append({"bufferView":len(bufferViews)-1,"componentType":5126,"count":cnt,"type":"VEC3","min":minv,"max":maxv})
        start=len(bin_blob); nf=[c for v in m.get("normals",[]) for c in v] or [0.0]*(cnt*3)
        bin_blob += struct.pack("<%sf"%len(nf), *nf)
        if len(bin_blob)%4: bin_blob += b"\x00"*(4-len(bin_blob)%4)
        bufferViews.append({"buffer":0,"byteOffset":start,"byteLength":len(bin_blob)-start})
        accessors.append({"bufferView":len(bufferViews)-1,"componentType":5126,"count":cnt,"type":"VEC3"})
        gltf_meshes.append({"primitives":[{"attributes":{"POSITION":len(accessors)-2,"NORMAL":len(accessors)-1},"mode":4}]})
        tx,ty,tz=m.get("translation",(0,0,0))
        nodes.append({"mesh":len(gltf_meshes)-1,"name":m.get("name","part"),"translation":[tx,ty,tz]})
    gltf={"asset":{"version":"2.0"},"scene":0,"scenes":[{"nodes":list(range(len(nodes)))}],
          "buffers":[{"byteLength":len(bin_blob)}],"bufferViews":bufferViews,"accessors":accessors,"meshes":gltf_meshes,"nodes":nodes}
    jb=json.dumps(gltf,separators=(",",":")).encode("utf-8")
    if len(jb)%4: jb+=b" "*(4-len(jb)%4)
    total=12+8+len(jb)+8+len(bin_blob)
    glb=b"glTF"+struct.pack("<I",2)+struct.pack("<I",total)
    glb+=struct.pack("<I",len(jb))+b"JSON"+jb
    glb+=struct.pack("<I",len(bin_blob))+b"BIN\x00"+bin_blob
    return glb

def read_ascii_stl(p: Path):
    pos=[]; nrm=[]; vx=[]; nx=ny=nz=0.0
    for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
        t=line.strip().split()
        if not t: continue
        if t[0]=="facet" and t[1]=="normal":
            nx,ny,nz=map(float,t[-3:])
        elif t[0]=="vertex":
            vx.append(tuple(map(float,t[1:4])))
            if len(vx)==3: pos.extend([vx[0],vx[1],vx[2]]); nrm.extend([(nx,ny,nz)]*3); vx.clear()
    return pos,nrm

def j58_parts(wall=2.0, seg=128, z0=0.0):
    # 단위 mm, 간단 근사
    L=5000.0; Rc=650.0
    parts=[]
    # Inlet spike + cowl
    v,f = lathe_solid([(z0,120.0),(z0+1200.0,450.0)], wall, seg); parts.append(("J58_Inlet_Spike.stl",v,f))
    v,f = ring_disk(500.0, 800.0, 300.0, seg, z0+1100.0); parts.append(("J58_Inlet_Cowl.stl",v,f))
    # Compressor case
    v,f = tube(Rc, wall, 1600.0, seg, z0+1400.0); parts.append(("J58_Compressor_Case.stl",v,f))
    # Combustor liner
    v,f = tube(Rc*0.9, wall, 700.0, seg, z0+3000.0); parts.append(("J58_Combustor_Liner.stl",v,f))
    # Turbine case
    v,f = tube(Rc*0.85, wall, 500.0, seg, z0+3700.0); parts.append(("J58_Turbine_Case.stl",v,f))
    # Afterburner case
    v,f = tube(Rc*0.95, wall, 600.0, seg, z0+4200.0); parts.append(("J58_Afterburner_Case.stl",v,f))
    # Convergent-divergent nozzle
    v,f = nozzle_cd(R_inlet=Rc*0.95, R_throat=Rc*0.55, R_exit=Rc*0.80, Lc=180.0, Ld=420.0, wall=wall, seg=seg, z0=z0+4600.0)
    parts.append(("J58_Nozzle_CD.stl",v,f))
    # Bypass ducts (left/right)
    v,f = elbow_90(Rc=500.0, r_out=140.0, wall=8.0, seg_phi=18, seg_theta=24, z0=z0+2600.0); parts.append(("J58_Bypass_Duct_L.stl",v,f))
    v=[(x,-y,z) for (x,y,z) in v]; parts.append(("J58_Bypass_Duct_R.stl",v,f))
    return parts

@api.post("/cad/j58_build")
def j58_build(body:dict=Body(None)):
    p=body or {}
    seg=int(p.get("segments",128)); wall=float(p.get("wall_t_mm",2.0))
    run = RUNS/f"run-{datetime.now():%Y%m%d-%H%M%S}-J58"
    run.mkdir(parents=True, exist_ok=True)
    names=[]
    for name,v,f in j58_parts(wall,seg,0.0):
        write_ascii_stl(run/name, v, f, name[:-4]); names.append(name)
    meta={"ok":True,"engine":"J58","run_rel":str(run.relative_to(DATA)).replace("\\","/"),"parts":names}
    (run/"meta.json").write_text(json.dumps(meta,indent=2),encoding="utf-8")
    return meta

@api.post("/cad/j58_assembly")
def j58_assembly(body:dict=Body(None)):
    p=body or {}
    explode=float(p.get("explode_mm",0.0))
    # 최신 런 찾기
    import re
    pat=re.compile(r"run-.*-J58$")
    c=[d for d in RUNS.iterdir() if d.is_dir() and pat.search(d.name)]
    if not c: return {"ok":False,"reason":"no_run"}
    run=sorted(c)[-1]
    # 파츠 로드
    meshes=[]
    for stl in sorted([x for x in run.iterdir() if x.suffix.lower()==".stl"]):
        pos,nrm=read_ascii_stl(stl)
        meshes.append({"name":stl.name,"positions":pos,"normals":nrm,"translation":(0,0,0)})
    glb=pack_glb(meshes)
    out=run/"j58_assembly.glb"; out.write_bytes(glb)
    rel=str(out.relative_to(DATA)).replace("\\","/")
    return {"ok":True,"glb_rel":rel}
