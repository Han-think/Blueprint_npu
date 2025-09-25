from __future__ import annotations
from fastapi import APIRouter, Body
from pathlib import Path
import struct, json, sys

api = APIRouter(prefix="/wb", tags=["glbtools"])
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT/"data"

def _read_stl_ascii(txt:str):
    pos=[]; nrm=[]; vx=[]; nx=ny=nz=0.0
    for line in txt.splitlines():
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

def _read_stl_binary(b:bytes):
    # 80B header + u32 tri_count + tri*(12f + u16)
    if len(b) < 84: return [],[]
    tri_count = struct.unpack_from("<I", b, 80)[0]
    pos=[]; nrm=[]
    off=84; step=50  # 12 floats(48B)+attr(2B)
    for _ in range(tri_count):
        nx,ny,nz, x1,y1,z1, x2,y2,z2, x3,y3,z3 = struct.unpack_from("<12f", b, off)
        off += step
        pos.extend([(x1,y1,z1),(x2,y2,z2),(x3,y3,z3)])
        nrm.extend([(nx,ny,nz)]*3)
    return pos,nrm

def read_stl(p: Path):
    b = p.read_bytes()
    # ASCII 힌트 여부
    is_ascii = b[:5].lower()==b"solid" and b.find(b"facet normal")!=-1
    if is_ascii:
        try:
            return _read_stl_ascii(b.decode("utf-8", errors="ignore"))
        except Exception:
            pass
    # 바이너리 시도
    return _read_stl_binary(b)

def pack_glb(meshes):
    bufferViews=[]; accessors=[]; gltf_meshes=[]; nodes=[]; bin_blob=b""
    for m in meshes:
        start=len(bin_blob); pf=[c for v in m["positions"] for c in v]
        if not pf: continue
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
        nodes.append({"mesh":len(gltf_meshes)-1,"name":m.get("name","part"),"translation":[0,0,0]})
    gltf={"asset":{"version":"2.0"},"scene":0,"scenes":[{"nodes":list(range(len(nodes)))}],
          "buffers":[{"byteLength":len(bin_blob)}],"bufferViews":bufferViews,"accessors":accessors,"meshes":gltf_meshes,"nodes":nodes}
    jb=json.dumps(gltf,separators=(",",":")).encode("utf-8")
    if len(jb)%4: jb+=b" "*(4-len(jb)%4)
    total=12+8+len(jb)+8+len(bin_blob)
    glb=b"glTF"+struct.pack("<I",2)+struct.pack("<I",total)
    glb+=struct.pack("<I",len(jb))+b"JSON"+jb
    glb+=struct.pack("<I",len(bin_blob))+b"BIN\x00"+bin_blob
    return glb

@api.post("/cad/pack_dir_glb")
def pack_dir_glb(body:dict=Body(...)):
    rel_dir = str(body.get("rel_dir","")).strip("/")
    out_name = body.get("out_name","assembly.glb")
    sort_key = body.get("sort","name")
    base=(DATA/rel_dir).resolve()
    if not base.exists(): return {"ok":False,"reason":"dir_not_found"}
    stls=sorted([p for p in base.iterdir() if p.suffix.lower()==".stl"], key=(lambda p: p.name if sort_key=="name" else p.stat().st_mtime))
    if not stls:
        # STL 없으면 같은 폴더의 GLB 하나를 복사
        glbs=sorted([p for p in base.iterdir() if p.suffix.lower()==".glb"])
        if not glbs: return {"ok":False,"reason":"no_stl_or_glb"}
        (base/out_name).write_bytes(glbs[0].read_bytes())
        rel=str((base/out_name).relative_to(DATA)).replace("\\","/")
        return {"ok":True,"glb_rel":rel,"count":0,"copied_from":glbs[0].name}
    meshes=[]
    for p in stls:
        pos,nrm=read_stl(p)
        meshes.append({"name":p.name,"positions":pos,"normals":nrm})
    glb=pack_glb(meshes)
    out=(base/out_name).resolve(); out.write_bytes(glb)
    rel=str(out.relative_to(DATA)).replace("\\","/")
    return {"ok":True,"glb_rel":rel,"count":len(stls)}
