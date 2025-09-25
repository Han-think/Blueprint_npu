from __future__ import annotations
from fastapi import APIRouter, Body
from pathlib import Path
import struct, json

api = APIRouter(prefix="/wb", tags=["glbtools"])
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT/"data"

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
        if len(bin_blob)%4: bin_blob += b"\\x00"*(4-len(bin_blob)%4)
        bufferViews.append({"buffer":0,"byteOffset":start,"byteLength":len(bin_blob)-start})
        cnt=len(m["positions"]); minv=[min(v[i] for v in m["positions"]) for i in range(3)]
        maxv=[max(v[i] for v in m["positions"]) for i in range(3)]
        accessors.append({"bufferView":len(bufferViews)-1,"componentType":5126,"count":cnt,"type":"VEC3","min":minv,"max":maxv})
        start=len(bin_blob); nf=[c for v in m.get("normals",[]) for c in v] or [0.0]*(cnt*3)
        bin_blob += struct.pack("<%sf"%len(nf), *nf)
        if len(bin_blob)%4: bin_blob += b"\\x00"*(4-len(bin_blob)%4)
        bufferViews.append({"buffer":0,"byteOffset":start,"byteLength":len(bin_blob)-start})
        accessors.append({"bufferView":len(bufferViews)-1,"componentType":5126,"count":cnt,"type":"VEC3"})
        gltf_meshes.append({"primitives":[{"attributes":{"POSITION":len(accessors)-2,"NORMAL":len(accessors)-1},"mode":4}]})
        nodes.append({"mesh":len(gltf_meshes)-1,"name":m.get("name","part"),"translation":[0,0,0]})
    gltf={"asset":{"version":"2.0"},"scene":0,"scenes":[{"nodes":list(range(len(nodes)))}],
          "buffers":[{"byteLength":len(bin_blob)}],"bufferViews":bufferViews,"accessors":accessors,"meshes":gltf_meshes,"nodes":nodes}
    jb=json.dumps(gltf,separators=(",",":")).encode("utf-8")
    if len(jb)%4: jb+=b" "*(4-len(jb)%4)
    total=12+8+len(jb)+8+len(bin_blob)
    glb=b"glTF"+struct.pack("<I",2)+struct.pack("<I",total)
    glb+=struct.pack("<I",len(jb))+b"JSON"+jb
    glb+=struct.pack("<I",len(bin_blob))+b"BIN\\x00"+bin_blob
    return glb

@api.post("/cad/pack_dir_glb")
def pack_dir_glb(body:dict=Body(...)):
    rel_dir = body.get("rel_dir","").strip("/")         # DATA 기준 상대경로
    out_name = body.get("out_name","assembly.glb")
    sort_key = body.get("sort","name")
    base=(DATA/rel_dir).resolve()
    if not base.exists(): return {"ok":False,"reason":"dir_not_found"}
    stls=sorted([p for p in base.iterdir() if p.suffix.lower()==".stl"], key=(lambda p: p.name if sort_key=="name" else p.stat().st_mtime))
    meshes=[]
    for p in stls:
        pos,nrm=read_ascii_stl(p)
        meshes.append({"name":p.name,"positions":pos,"normals":nrm})
    glb=pack_glb(meshes)
    out=(base/out_name).resolve(); out.write_bytes(glb)
    rel=str(out.relative_to(DATA)).replace("\\","/")
    return {"ok":True,"glb_rel":rel,"count":len(stls)}
