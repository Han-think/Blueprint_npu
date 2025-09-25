from __future__ import annotations
from fastapi import APIRouter, Body, Query
from fastapi.responses import JSONResponse, FileResponse
from pathlib import Path
import struct, json, re, datetime

api = APIRouter(prefix="/wb", tags=["saturn"])
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT/"data"
RUNS = DATA/"geometry/cad/saturn_cad_runs"
RUNS.mkdir(parents=True, exist_ok=True)

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

def pack_glb(meshes):
    bufferViews=[]; accessors=[]; gltf_meshes=[]; nodes=[]; bin_blob=b""
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

def _last_run(stage):
    pat=re.compile(rf"run-.*-{stage}$")
    c=[d for d in RUNS.iterdir() if d.is_dir() and pat.search(d.name)]
    return sorted(c)[-1] if c else None

def _add(parts, run, name, tr=(0,0,0)):
    p=run/name
    if p.exists():
        pos,nrm=read_ascii_stl(p); parts.append({"name":name,"positions":pos,"normals":nrm,"translation":tr})

@api.get("/cad/saturn_stack_assembly")
def saturn_stack_assembly(mode: str = Query("outer", enum=["outer","full"])):
    r1=_last_run("S-IC"); r2=_last_run("S-II"); r3=_last_run("S-IVB")
    if not all([r1,r2,r3]): return JSONResponse({"ok":False,"reason":"missing_runs"}, status_code=400)
    L1,L2,L3 = 42100,24900,17800; GAP=1200
    z1=0; z2=L1+GAP; z3=L1+GAP+L2+GAP
    parts=[]
    # S-IC
    if r1:
        _add(parts,r1,"SIC_shell.stl",(0,0,z1))
        if mode!="outer":
            for n in ["SIC_LOX_tank.stl","SIC_Intertank_ring.stl","SIC_RP1_tank.stl","SIC_Thrust_ring.stl",
                      "SIC_Thrust_beam_0.stl","SIC_Thrust_beam_1.stl","SIC_Engine_mount_ring.stl",
                      "SIC_LOX_pipe_vert.stl","SIC_LOX_elbow.stl","SIC_Fin_rect.stl"]:
                _add(parts,r1,n,(0,0,z1))
            # F-1 파츠 복제 배치
            engine_files=[p.name for p in r1.iterdir() if p.suffix.lower()==".stl" and p.name.startswith("F1_")]
            offs=[(-2500,0,-3000),(2500,0,-3000),(0,0,-3000),(-1250,-2165,-3000),(1250,2165,-3000)]
            for (dx,dy,dz) in offs:
                for ef in engine_files: _add(parts,r1,ef,(dx,dy,z1+dz))
    # S-II
    if r2:
        _add(parts,r2,"SII_shell.stl",(0,0,z2))
        if mode!="outer":
            for n in ["SII_LOX_tank.stl","SII_CB_up.stl","SII_CB_dn.stl","SII_CB_insul.stl","SII_LH2_tank.stl"]:
                _add(parts,r2,n,(0,0,z2))
            engine_files=[p.name for p in r2.iterdir() if p.suffix.lower()==".stl" and p.name.startswith("J2_")]
            offs=[(-1800,0,-2200),(1800,0,-2200),(0,0,-2200),(-900,-1550,-2200),(900,1550,-2200)]
            for (dx,dy,dz) in offs:
                for ef in engine_files: _add(parts,r2,ef,(dx,dy,z2+dz))
    # S-IVB
    if r3:
        _add(parts,r3,"SIVB_shell.stl",(0,0,z3))
        if mode!="outer":
            for n in ["SIVB_LOX_tank.stl","SIVB_LH2_tank.stl","SIVB_LH2_baffle_0.stl","SIVB_LH2_baffle_1.stl","SIVB_IU_ring.stl"]:
                _add(parts,r3,n,(0,0,z3))
            engine_files=[p.name for p in r3.iterdir() if p.suffix.lower()==".stl" and p.name.startswith("J2_")]
            for ef in engine_files: _add(parts,r3,ef,(0,0,z3-2200))
    glb=pack_glb(parts)
    out = RUNS/f"run-{datetime.datetime.now():%Y%m%d-%H%M%S}-STACK/stack_full.glb" if mode=="full" else RUNS/f"run-{datetime.datetime.now():%Y%m%d-%H%M%S}-STACK/stack_assembly.glb"
    out.parent.mkdir(parents=True, exist_ok=True); out.write_bytes(glb)
    rel=str(out.relative_to(DATA)).replace("\\","/")
    return {"ok":True,"glb_rel":rel,"mode":mode}
