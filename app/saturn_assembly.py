from __future__ import annotations
from fastapi import APIRouter, Body
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
            if len(vx)==3:
                pos.extend([vx[0],vx[1],vx[2]])
                nrm.extend([(nx,ny,nz)]*3); vx.clear()
    return pos,nrm

def pack_glb(meshes):
    buffers=[]; bufferViews=[]; accessors=[]; nodes=[]; gltf_meshes=[]
    bin_blob=b""
    for m in meshes:
        start=len(bin_blob)
        pf=[c for v in m["positions"] for c in v]
        bin_blob += struct.pack("<%sf"%len(pf), *pf)
        if len(bin_blob)%4: bin_blob += b"\x00"*(4-len(bin_blob)%4)
        bufferViews.append({"buffer":0,"byteOffset":start,"byteLength":len(bin_blob)-start})
        count=len(m["positions"])
        minv=[min(v[i] for v in m["positions"]) for i in range(3)]
        maxv=[max(v[i] for v in m["positions"]) for i in range(3)]
        accessors.append({"bufferView":len(bufferViews)-1,"componentType":5126,"count":count,"type":"VEC3","min":minv,"max":maxv})
        start=len(bin_blob)
        nf=[c for v in m.get("normals",[]) for c in v] or [0.0]*(count*3)
        bin_blob += struct.pack("<%sf"%len(nf), *nf)
        if len(bin_blob)%4: bin_blob += b"\x00"*(4-len(bin_blob)%4)
        bufferViews.append({"buffer":0,"byteOffset":start,"byteLength":len(bin_blob)-start})
        accessors.append({"bufferView":len(bufferViews)-1,"componentType":5126,"count":count,"type":"VEC3"})
        gltf_meshes.append({"primitives":[{"attributes":{"POSITION":len(accessors)-2,"NORMAL":len(accessors)-1},"mode":4}]})
        tx,ty,tz=m.get("translation",(0,0,0))
        nodes.append({"mesh":len(gltf_meshes)-1,"name":m.get("name","part"),"translation":[tx,ty,tz]})
    gltf={"asset":{"version":"2.0"},"scene":0,"scenes":[{"nodes":list(range(len(nodes)))}],
          "buffers":[{"byteLength":len(bin_blob)}],"bufferViews":bufferViews,"accessors":accessors,
          "meshes":gltf_meshes,"nodes":nodes}
    jb=json.dumps(gltf,separators=(",",":")).encode("utf-8")
    if len(jb)%4: jb+=b" "*(4-len(jb)%4)
    total=12+8+len(jb)+8+len(bin_blob)
    glb=b"glTF"+struct.pack("<I",2)+struct.pack("<I",total)
    glb+=struct.pack("<I",len(jb))+b"JSON"+jb
    glb+=struct.pack("<I",len(bin_blob))+b"BIN"+bin_blob
    return glb

def _last_run(stage):
    pat=re.compile(rf"run-.*-{stage}$")
    c=[d for d in RUNS.iterdir() if d.is_dir() and pat.search(d.name)]
    return sorted(c)[-1] if c else None

@api.post("/cad/saturn_stage_assembly")
def saturn_stage_assembly(body:dict=Body(None)):
    b=body or {}
    stage=str(b.get("stage","S-IC")).upper()
    run=_last_run(stage)
    if not run: return JSONResponse({"ok":False,"reason":"no_stl_run"}, status_code=400)
    meshes=[]
    if stage=="S-IC":
        shell=run/"SIC_shell.stl"; f1=run/"F1_placeholder.stl"
        p,n=read_ascii_stl(shell); meshes.append({"name":"SIC_shell","positions":p,"normals":n})
        offs=[(-2500,0,-3000),(2500,0,-3000),(0,0,-3000),(-1250,-2165,-3000),(1250,2165,-3000)]
        if f1.exists():
            p,n=read_ascii_stl(f1)
            for dx,dy,dz in offs: meshes.append({"name":"F1","positions":p,"normals":n,"translation":(dx,dy,dz)})
    elif stage=="S-II":
        shell=run/"SII_shell.stl"; j2=run/"J2_placeholder.stl"
        p,n=read_ascii_stl(shell); meshes.append({"name":"SII_shell","positions":p,"normals":n})
        offs=[(-1800,0,-2200),(1800,0,-2200),(0,0,-2200),(-900,-1550,-2200),(900,1550,-2200)]
        if j2.exists():
            p,n=read_ascii_stl(j2)
            for dx,dy,dz in offs: meshes.append({"name":"J2","positions":p,"normals":n,"translation":(dx,dy,dz)})
    else:
        shell=run/"SIVB_shell.stl"; j2=run/"J2_placeholder.stl"
        p,n=read_ascii_stl(shell); meshes.append({"name":"SIVB_shell","positions":p,"normals":n})
        if j2.exists():
            p,n=read_ascii_stl(j2); meshes.append({"name":"J2","positions":p,"normals":n,"translation":(0,0,-2200)})
    glb=pack_glb(meshes)
    out=run/"stage_assembly.glb"; out.write_bytes(glb)
    rel=str(out.relative_to(Path("data"))).replace("\\","/")
    return {"ok":True,"glb_rel":rel}

@api.get("/cad/saturn_stack_assembly")
def saturn_stack_assembly():
    r1=_last_run("S-IC"); r2=_last_run("S-II"); r3=_last_run("S-IVB")
    if not all([r1,r2,r3]): return JSONResponse({"ok":False,"reason":"missing_runs"}, status_code=400)
    L1,L2,L3 = 42100, 24900, 17800; GAP=1200
    z1=0; z2=L1+GAP; z3=L1+GAP+L2+GAP
    meshes=[]
    for run,name,z in ((r1,"SIC_shell.stl",z1),(r2,"SII_shell.stl",z2),(r3,"SIVB_shell.stl",z3)):
        p=run/name
        if p.exists():
            pos,nrm=read_ascii_stl(p)
            meshes.append({"name":name,"positions":pos,"normals":nrm,"translation":(0,0,z)})
    glb=pack_glb(meshes)
    out = RUNS/f"run-{datetime.datetime.now():%Y%m%d-%H%M%S}-STACK/stack_assembly.glb"
    out.parent.mkdir(parents=True, exist_ok=True); out.write_bytes(glb)
    rel=str(out.relative_to(Path("data"))).replace("\\","/")
    return {"ok":True,"glb_rel":rel}

# 안전 파일 서빙(중복되면 기존 것 사용)
@api.get("/files/{rel_path:path}")
def send_file(rel_path:str):
    base=(ROOT/"data").resolve()
    full=(base/rel_path).resolve()
    if not str(full).startswith(str(base)) or not full.exists():
        return JSONResponse({"ok":False,"reason":"not_found","rel":rel_path}, status_code=404)
    return FileResponse(str(full))
