from __future__ import annotations
from fastapi import APIRouter, Body
from pathlib import Path
import struct, json, re, math

api = APIRouter(prefix="/wb", tags=["glbpack_named"])
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT/"data"

# ── STL 리더(ASCII/바이너리)
def _read_stl_ascii(b:bytes):
    txt=b.decode("utf-8",errors="ignore")
    pos=[]; nrm=[]; vx=[]; nx=ny=nz=0.0
    for line in txt.splitlines():
        t=line.strip().split()
        if not t: continue
        if t[0]=="facet" and t[1]=="normal": nx,ny,nz=map(float,t[-3:])
        elif t[0]=="vertex":
            vx.append(tuple(map(float,t[1:4])))
            if len(vx)==3:
                pos.extend([vx[0],vx[1],vx[2]]); nrm.extend([(nx,ny,nz)]*3); vx.clear()
    return pos,nrm
def _read_stl_binary(b:bytes):
    if len(b)<84: return [],[]
    tri_count=struct.unpack_from("<I",b,80)[0]
    pos=[]; nrm=[]; off=84
    for _ in range(tri_count):
        nx,ny,nz, x1,y1,z1, x2,y2,z2, x3,y3,z3 = struct.unpack_from("<12f", b, off)
        off+=50
        pos.extend([(x1,y1,z1),(x2,y2,z2),(x3,y3,z3)])
        nrm.extend([(nx,ny,nz)]*3)
    return pos,nrm
def read_stl(p:Path):
    b=p.read_bytes()
    is_ascii = b[:5].lower()==b"solid" and (b.find(b"facet normal")!=-1)
    if is_ascii:
        try: return _read_stl_ascii(b)
        except: pass
    return _read_stl_binary(b)

# ── 그룹 규칙(필요시 확장 가능)
DEFAULT_GROUPS = {
  "Inlet":        ["SPIKE","INLET","COWL","DIFFUSER"],
  "Compressor":   ["COMP","COMPRESSOR","STATOR","ROTOR","CASE"],
  "Combustor":    ["COMB","BURNER","LINER","FUEL"],
  "Turbine":      ["TURB","NGV","TURBINE"],
  "Afterburner":  ["AFTERBURNER","AB","FLAMEHOLDER","AUGMENTOR"],
  "Nozzle":       ["NOZZLE","CD","CORENOZZLE"],
  "Bypass":       ["BYPASS","DUCT","MIXER"],
  "Bearing":      ["BEARING"],
  "Shaft":        ["SHAFT","HUB","DISK","DISC"],
  "Mounts":       ["MOUNT","STRUT","FRAME","RING"],
  "Pipes":        ["PIPE","TUBE","MANIFOLD"],
  "GearsBelts":   ["GEAR","BELT","CHAIN"],
  "Casing":       ["CASING","CASE","SHELL"],
  "Misc":         []
}
_RE_L = re.compile(r"(^|[_\-.])L($|[_\-.])", re.I)
_RE_R = re.compile(r"(^|[_\-.])R($|[_\-.])", re.I)

# ── GLB 패킹(계층/노드 지원)
def pack_glb_hier(meshes, hierarchy):
    bin_blob=b""; bufferViews=[]; accessors=[]; gltf_meshes=[]; nodes=[]
    root_nodes=[]
    node_index={}
    def add_node(name, parent=None, mesh_idx=None):
        idx=len(nodes)
        n={"name":name}
        if mesh_idx is not None: n["mesh"]=mesh_idx
        nodes.append(n)
        if parent is None: root_nodes.append(idx)
        else:
            nodes[parent].setdefault("children",[]).append(idx)
        node_index[name]=idx
        return idx
    # 루트 그룹 + 좌/우/센터 그룹 생성
    for g in hierarchy.keys():
        gi = add_node(g, None, None)
        for side in ("Left","Right","Center"):
            add_node(f"{g}/{side}", gi, None)
    # 파트 메쉬 생성
    for part in meshes:
        # position
        pf=[c for v in part["positions"] for c in v]
        if not pf: continue
        start=len(bin_blob); bin_blob+=struct.pack("<%sf"%len(pf), *pf)
        if len(bin_blob)%4: bin_blob+=b"\x00"*(4-len(bin_blob)%4)
        bufferViews.append({"buffer":0,"byteOffset":start,"byteLength":len(bin_blob)-start})
        cnt=len(part["positions"])
        minv=[min(v[i] for v in part["positions"]) for i in range(3)]
        maxv=[max(v[i] for v in part["positions"]) for i in range(3)]
        accessors.append({"bufferView":len(bufferViews)-1,"componentType":5126,"count":cnt,"type":"VEC3","min":minv,"max":maxv})
        # normal
        nf=[c for v in part.get("normals",[]) for c in v] or [0.0]*(cnt*3)
        start=len(bin_blob); bin_blob+=struct.pack("<%sf"%len(nf), *nf)
        if len(bin_blob)%4: bin_blob+=b"\x00"*(4-len(bin_blob)%4)
        bufferViews.append({"buffer":0,"byteOffset":start,"byteLength":len(bin_blob)-start})
        accessors.append({"bufferView":len(bufferViews)-1,"componentType":5126,"count":cnt,"type":"VEC3"})
        # mesh + node
        gltf_meshes.append({"primitives":[{"attributes":{"POSITION":len(accessors)-2,"NORMAL":len(accessors)-1},"mode":4}]})
        # 소속 부모 노드
        parent_name = part["parent_path"]  # 예: "Bearing/Left"
        parent_idx = node_index.get(parent_name)
        add_node(part["name"], parent_idx, len(gltf_meshes)-1)
    gltf={"asset":{"version":"2.0"},"scene":0,
          "scenes":[{"nodes":root_nodes}],
          "buffers":[{"byteLength":len(bin_blob)}],
          "bufferViews":bufferViews,"accessors":accessors,"meshes":gltf_meshes,"nodes":nodes}
    jb=json.dumps(gltf,separators=(",",":")).encode("utf-8")
    if len(jb)%4: jb+=b" "*(4-len(jb)%4)
    total=12+8+len(jb)+8+len(bin_blob)
    glb=b"glTF"+struct.pack("<I",2)+struct.pack("<I",total)
    glb+=struct.pack("<I",len(jb))+b"JSON"+jb
    glb+=struct.pack("<I",len(bin_blob))+b"BIN\x00"+bin_blob
    return glb, {"root_nodes":[n for n in hierarchy.keys()]}

def _classify(name:str, groups:dict):
    u=name.upper()
    group="Misc"
    for g,keys in groups.items():
        for k in keys:
            if k and k in u:
                group=g; break
        if group!= "Misc": break
    side="Center"
    if _RE_L.search(u) and not _RE_R.search(u): side="Left"
    elif _RE_R.search(u) and not _RE_L.search(u): side="Right"
    return group, side

@api.post("/cad/pack_dir_glb_hier")
def pack_dir_glb_hier(body:dict=Body(...)):
    rel_dir = str(body.get("rel_dir","")).strip("/")
    out_name = body.get("out_name","assembly_named.glb")
    groups = body.get("groups") or DEFAULT_GROUPS
    base=(DATA/rel_dir).resolve()
    if not base.exists(): return {"ok":False,"reason":"dir_not_found"}
    stls=sorted([p for p in base.iterdir() if p.suffix.lower()==".stl"], key=lambda p: p.name)
    if not stls: return {"ok":False,"reason":"no_stl"}
    meshes=[]; manifest={}
    for p in stls:
        pos,nrm = read_stl(p)
        nm=p.stem
        g,side=_classify(nm, groups)
        parent=f"{g}/{side}"
        meshes.append({"name":nm, "positions":pos, "normals":nrm, "parent_path":parent})
        manifest.setdefault(g,{}).setdefault(side,[]).append(nm)
    glb, meta = pack_glb_hier(meshes, groups)
    out=(base/out_name).resolve(); out.write_bytes(glb)
    man={"ok":True,"source":str(base.name),"groups":manifest}
    (base/(out_name+".manifest.json")).write_text(json.dumps(man,indent=2),encoding="utf-8")
    rel_glb=str(out.relative_to(DATA)).replace("\\","/")
    rel_manifest=str((out.parent/(out.name+".manifest.json")).relative_to(DATA)).replace("\\","/")
    return {"ok":True,"glb_rel":rel_glb,"manifest_rel":rel_manifest,"count":len(stls)}
