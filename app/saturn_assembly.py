from __future__ import annotations
from fastapi import APIRouter
from fastapi.responses import JSONResponse, FileResponse
from pathlib import Path
import struct, json, math, datetime, os, re

api = APIRouter(prefix="/wb", tags=["saturn"])
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT/"data"
RUNS = DATA/"geometry/cad/saturn_cad_runs"
RUNS.mkdir(parents=True, exist_ok=True)

# --- 간단 STL 파서(ASCII) ---
def read_ascii_stl(p: Path):
    pos=[]; nrm=[]
    vx=[]
    for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
        line=line.strip()
        if line.startswith("facet normal"):
            parts=line.split()
            nx,ny,nz=map(float,parts[-3:])
        elif line.startswith("vertex"):
            _,x,y,z=line.split()
            vx.append((float(x),float(y),float(z)))
            if len(vx)==3:
                # 한 면 완성
                pos.extend([vx[0],vx[1],vx[2]])
                nrm.extend([(nx,ny,nz)]*3)
                vx.clear()
    return pos,nrm

def pack_glb(meshes):
    # meshes: [{ "name":str, "positions":[(x,y,z)...], "normals":[(x,y,z)...], "translation":(x,y,z) }]
    buffers=[]
    bufferViews=[]
    accessors=[]
    nodes=[]
    gltf_meshes=[]
    bin_blob=b""
    for i,m in enumerate(meshes):
        # positions
        start=len(bin_blob)
        pos_flat=[c for v in m["positions"] for c in v]
        bin_blob += struct.pack("<%sf"%len(pos_flat), *pos_flat)
        # align 4
        if len(bin_blob)%4: bin_blob += b"\x00"*(4-len(bin_blob)%4)
        bv_pos = {"buffer":0,"byteOffset":start,"byteLength":len(bin_blob)-start}
        bufferViews.append(bv_pos)
        count=len(m["positions"])
        minv=[min(v[j] for v in m["positions"]) for j in range(3)]
        maxv=[max(v[j] for v in m["positions"]) for j in range(3)]
        acc_pos={"bufferView":len(bufferViews)-1,"componentType":5126,"count":count,"type":"VEC3","min":minv,"max":maxv}
        accessors.append(acc_pos)

        # normals
        start=len(bin_blob)
        nrm_flat=[c for v in m["normals"] for c in v] if m.get("normals") else [0.0]*count*3
        bin_blob += struct.pack("<%sf"%len(nrm_flat), *nrm_flat)
        if len(bin_blob)%4: bin_blob += b"\x00"*(4-len(bin_blob)%4)
        bv_nrm={"buffer":0,"byteOffset":start,"byteLength":len(bin_blob)-start}
        bufferViews.append(bv_nrm)
        acc_nrm={"bufferView":len(bufferViews)-1,"componentType":5126,"count":count,"type":"VEC3"}
        accessors.append(acc_nrm)

        mesh={"primitives":[{"attributes":{"POSITION":len(accessors)-2,"NORMAL":len(accessors)-1}, "mode":4}]}
        gltf_meshes.append(mesh)
        tx,ty,tz=m.get("translation",(0,0,0))
        nodes.append({"mesh":len(gltf_meshes)-1,"name":m.get("name",f"part{i}"),"translation":[tx,ty,tz]})

    gltf={
        "asset":{"version":"2.0"},
        "scene":0,
        "scenes":[{"nodes":list(range(len(nodes)))}],
        "buffers":[{"byteLength":len(bin_blob)}],
        "bufferViews":bufferViews,
        "accessors":accessors,
        "meshes":gltf_meshes,
        "nodes":nodes,
    }
    json_bytes=json.dumps(gltf,separators=(",",":")).encode("utf-8")
    if len(json_bytes)%4: json_bytes += b" "*(4-len(json_bytes)%4)
    # GLB header
    total_len=12+8+len(json_bytes)+8+len(bin_blob)
    glb = b"glTF"+struct.pack("<I",2)+struct.pack("<I",total_len)
    glb += struct.pack("<I",len(json_bytes))+b"JSON"+json_bytes
    glb += struct.pack("<I",len(bin_blob))+b"BIN"+bin_blob
    return glb

def _ensure_stage_stls(stage:str):
    # 최신 run 폴더 찾기(없으면 생성)
    pattern=re.compile(rf"run-.*-{stage.replace('/','_')}$")
    candidates=[d for d in RUNS.iterdir() if d.is_dir() and pattern.search(d.name)]
    if not candidates:
        # 클라이언트에서 /cad/saturn_stage_build 호출해서 생성하는 흐름을 권장
        return None
    return sorted(candidates)[-1]

def _load_part(run:Path, name:str, tr=(0,0,0)):
    p=run/name
    if not p.exists(): return None
    pos,nrm=read_ascii_stl(p)
    return {"name":name, "positions":pos, "normals":nrm, "translation":tr}

@api.post("/cad/saturn_stage_assembly")
def saturn_stage_assembly(body:dict|None=None):
    b=body or {}
    stage=str(b.get("stage","S-IC")).upper()
    run=_ensure_stage_stls(stage)
    if run is None:
        return JSONResponse({"ok":False,"reason":"no_stl_run","hint":"먼저 /cad/saturn_stage_build 호출"}, status_code=400)

    meshes=[]
    if stage=="S-IC":
        meshes.append(_load_part(run,"SIC_shell.stl",(0,0,0)) )
        # 엔진 더미 5기 배치(대충 원형 오프셋)
        for (dx,dy) in ((-2500,0),(2500,0),(0,0),(-1250,-2165),(1250,2165)):
            m=_load_part(run,"F1_placeholder.stl",(dx,dy,-3000))
            if m: meshes.append(m)
    elif stage=="S-II":
        meshes.append(_load_part(run,"SII_shell.stl",(0,0,0)) )
        for (dx,dy) in ((-1800,0),(1800,0),(0,0),(-900,-1550),(900,1550)):
            m=_load_part(run,"J2_placeholder.stl",(dx,dy,-2200))
            if m: meshes.append(m)
    else:
        meshes.append(_load_part(run,"SIVB_shell.stl",(0,0,0)) )
        m=_load_part(run,"J2_placeholder.stl",(0,0,-2200))
        if m: meshes.append(m)

    meshes=[m for m in meshes if m]
    glb=pack_glb(meshes)
    out = run/"stage_assembly.glb"
    out.write_bytes(glb)
    rel = str(out.relative_to(Path("data"))).replace("\\","/")
    return {"ok":True,"glb_rel":rel}

@api.get("/cad/saturn_stack_assembly")
def saturn_stack_assembly():
    # 각 최신 run 폴더에서 셸만 불러 간단 스택
    def last(stage):
        pattern=re.compile(rf"run-.*-{stage}$")
        c=[d for d in RUNS.iterdir() if d.is_dir() and pattern.search(d.name)]
        return sorted(c)[-1] if c else None
    r1=last("S-IC"); r2=last("S-II"); r3=last("S-IVB")
    if not all([r1,r2,r3]):
        return JSONResponse({"ok":False,"reason":"missing_runs","hint":"S-IC/S-II/S-IVB 먼저 빌드"}, status_code=400)

    # 대충 높이(mm)
    L1,L2,L3 = 42100, 24900, 17800
    GAP=1200
    z1=0; z2=L1+GAP; z3=L1+GAP+L2+GAP

    meshes=[]
    # 셸만 사용(엔진은 각 단 어셈블리에서 확인)
    for (run,name,z) in ((r1,"SIC_shell.stl",z1),(r2,"SII_shell.stl",z2),(r3,"SIVB_shell.stl",z3)):
        p = run/name
        if p.exists():
            pos,nrm=read_ascii_stl(p)
            meshes.append({"name":name,"positions":pos,"normals":nrm,"translation":(0,0,z)})

    glb=pack_glb(meshes)
    out = RUNS/f"run-{datetime.datetime.now():%Y%m%d-%H%M%S}-STACK/stack_assembly.glb"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(glb)
    rel = str(out.relative_to(Path("data"))).replace("\\","/")
    return {"ok":True,"glb_rel":rel}
