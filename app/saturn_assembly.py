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

def _last_run(stage):
    pat=re.compile(rf"run-.*-{stage}$")
    c=[d for d in RUNS.iterdir() if d.is_dir() and pat.search(d.name)]
    return sorted(c)[-1] if c else None

@api.post("/cad/saturn_stage_assembly")
def saturn_stage_assembly(body:dict=Body(None), mode:str="interior"):
    b=body or {}
    stage=str(b.get("stage","S-IC")).upper()
    explode=float(b.get("explode_mm", 0.0))
    run=_last_run(stage)
    if not run: return JSONResponse({"ok":False,"reason":"no_stl_run"}, status_code=400)

    parts=[]
    def add(name, tr=(0,0,0)):
        p=run/name
        if p.exists():
            pos,nrm=read_ascii_stl(p); parts.append({"name":name,"positions":pos,"normals":nrm,"translation":tr})

    if stage=="S-IC":
        L=42100.0; inter=900.0; l_lox=L*0.42; l_rp1=L-l_lox-inter
        add("SIC_shell.stl")
        if mode!="outer":
            add("SIC_LOX_tank.stl",(0,0,explode))
            add("SIC_Intertank_ring.stl",(0,0,2*explode))
            add("SIC_RP1_tank.stl",(0,0,3*explode))
            add("SIC_Thrust_ring.stl",(0,0,4*explode))
        # 엔진 5기 배치
        offs=[(-2500,0,-3000),(2500,0,-3000),(0,0,-3000),(-1250,-2165,-3000),(1250,2165,-3000)]
        if (run/"F1_placeholder.stl").exists():
            pos,nrm=read_ascii_stl(run/"F1_placeholder.stl")
            for i,(dx,dy,dz) in enumerate(offs):
                parts.append({"name":f"F1_{i}","positions":pos,"normals":nrm,"translation":(dx,dy,dz-5*explode)})
        if (run/"SIC_Fin_rect.stl").exists() and mode!="outer":
            # 4개 복제 회전 대신 평행 이동으로 간단 표시
            for dx,dy in ((0,0),(0,0),(0,0),(0,0)):
                add("SIC_Fin_rect.stl",(0,0,0))

    elif stage=="S-II":
        add("SII_shell.stl")
        if mode!="outer":
            add("SII_LOX_tank.stl",(0,0,explode))
            add("SII_CommonBulkhead.stl",(0,0,2*explode))
            add("SII_LH2_tank.stl",(0,0,3*explode))
        if (run/"J2_placeholder.stl").exists():
            offs=[(-1800,0,-2200),(1800,0,-2200),(0,0,-2200),(-900,-1550,-2200),(900,1550,-2200)]
            pos,nrm=read_ascii_stl(run/"J2_placeholder.stl")
            for i,(dx,dy,dz) in enumerate(offs):
                parts.append({"name":f"J2_{i}","positions":pos,"normals":nrm,"translation":(dx,dy,dz-4*explode)})

    else:
        add("SIVB_shell.stl")
        if mode!="outer":
            add("SIVB_LOX_tank.stl",(0,0,explode))
            add("SIVB_LH2_tank.stl",(0,0,2*explode))
        if (run/"J2_placeholder.stl").exists():
            pos,nrm=read_ascii_stl(run/"J2_placeholder.stl")
            parts.append({"name":"J2","positions":pos,"normals":nrm,"translation":(0,0,-2200-3*explode)})

    glb=pack_glb(parts)
    out=run/"stage_assembly.glb"; out.write_bytes(glb)
    rel=str(out.relative_to(DATA)).replace("\\","/")
    return {"ok":True,"glb_rel":rel}

@api.get("/cad/saturn_stack_assembly")
def saturn_stack_assembly():
    def last(stage):
        import re
        pat=re.compile(rf"run-.*-{stage}$")
        c=[d for d in RUNS.iterdir() if d.is_dir() and pat.search(d.name)]
        return sorted(c)[-1] if c else None
    r1,last1 = last("S-IC"), "SIC_shell.stl"
    r2,last2 = last("S-II"), "SII_shell.stl"
    r3,last3 = last("S-IVB"), "SIVB_shell.stl"
    if not all([r1,r2,r3]): return JSONResponse({"ok":False,"reason":"missing_runs"}, status_code=400)
    L1,L2,L3 = 42100, 24900, 17800; GAP=1200
    z1=0; z2=L1+GAP; z3=L1+GAP+L2+GAP
    parts=[]
    for run,name,z in ((r1,last1,z1),(r2,last2,z2),(r3,last3,z3)):
        p=run/name
        if p.exists():
            pos,nrm=read_ascii_stl(p)
            parts.append({"name":name,"positions":pos,"normals":nrm,"translation":(0,0,z)})
    glb=pack_glb(parts)
    out = RUNS/f"run-{datetime.datetime.now():%Y%m%d-%H%M%S}-STACK/stack_assembly.glb"
    out.parent.mkdir(parents=True, exist_ok=True); out.write_bytes(glb)
    rel=str(out.relative_to(DATA)).replace("\\","/")
    return {"ok":True,"glb_rel":rel}

@api.get("/files/{rel_path:path}")
def send_file(rel_path:str):
    base=(ROOT/"data").resolve(); full=(base/rel_path).resolve()
    from fastapi.responses import FileResponse
    from fastapi import HTTPException
    if not str(full).startswith(str(base)) or not full.exists():
        raise HTTPException(status_code=404, detail="not_found")
    return FileResponse(str(full))

