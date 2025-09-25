from __future__ import annotations
from fastapi import APIRouter, Body
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import numpy as np, os, json, datetime, trimesh as tm, shutil

RUNS_V23 = os.path.join("data","geometry","cad","j58_v23_runs")
RUNS_OLD = os.path.join("data","geometry","cad","j58_runs")
os.makedirs(RUNS_V23, exist_ok=True)

def _safe(rel:str):
    base=os.path.abspath("data"); p=os.path.abspath(os.path.join(base, rel.replace("/", os.sep)))
    return p if p.startswith(base) else None

def rect_plate(w,d,t=2.0, z=0.0):
    m=tm.creation.box(extents=[w,d,t]); m.apply_translation([w*0.5,d*0.5,z+t*0.5]); return m

def load_mesh(path:str)->tm.Trimesh:
    m = tm.load(path) if path.lower().endswith(".stl") else tm.load_mesh(path)
    return m if isinstance(m, tm.Trimesh) else tm.util.concatenate(m.dump())

def _latest(dir_):
    if not os.path.isdir(dir_): return None
    runs=[d for d in sorted(os.listdir(dir_)) if d.startswith("run-")]
    return os.path.join(dir_, runs[-1]) if runs else None

def _load_meta(out_dir: str | None):
    cand=[]
    if out_dir: cand.append(out_dir)
    cand += [_latest(RUNS_V23), _latest(RUNS_OLD)]
    for r in cand:
        if not r: continue
        p1=os.path.join(r,"j58_v23_bom.json")
        p2=os.path.join(r,"j58_bom.json")
        if os.path.exists(p1): return json.load(open(p1,encoding="utf-8")), r, "v23"
        if os.path.exists(p2): return json.load(open(p2,encoding="utf-8")), r, "old"
    return None, None, None

CORE_KEYS=[("fan_rotor","fan_rotor"),("fan_stator","fan_stator"),
("comp_rotor","compressor_rotor"),("comp_stator","compressor_stator"),
("turb_rotor","turbine_rotor"),("turb_stator","turbine_stator"),
("seat_fan","seat_fan"),("seat_comp","seat_comp"),("seat_turb","seat_turb"),
("bearing_holder_L","bearing_holder_L"),("bearing_holder_R","bearing_holder_R"),
("bearing_rail_L","bearing_rail_L"),("bearing_rail_R","bearing_rail_R"),
("shaft_5mm","shaft_5mm")]+[(f"spacer_{i}",f"spacer_{i}") for i in range(1,7)]

SHELL_KEYS=[("inlet_spike","inlet_spike"),("combustor_shell","combustor_liner"),
("afterburner_shell","afterburner_case"),("nozzle_cone","nozzle_cone"),
("aft_cap","aft_cap"),("casing_front","outer_casing"),("casing_mid","outer_casing"),
("casing_aft","outer_casing"),("splice_front_mid","splice_front_mid"),
("splice_mid_aft","splice_mid_aft"),("pylon_mount_front","pylon_mount_front"),
("pylon_mount_aft","pylon_mount_aft")]

def _pick_named(meta:dict, tag:str, kind:str):
    names=[p["name"] for p in meta["parts"]]
    def choose(keys):
        outs=[]
        for k_new,k_old in keys:
            pref=(k_new+tag) if any(n.startswith(k_new+tag) for n in names) else k_new
            for cand in [pref, k_old+tag, k_old]:
                hit=next((p for p in meta["parts"] if p["name"].startswith(cand)), None)
                if hit: outs.append((hit["name"], hit["path"])); break
        return outs
    if kind=="core":   return choose(CORE_KEYS)
    if kind=="shells": return choose(SHELL_KEYS)
    return [(p["name"], p["path"]) for p in meta["parts"] if (tag in p["name"]) or ("_R" not in p["name"] and "_L" not in p["name"])]

def lay_flat(m:tm.Trimesh)->tm.Trimesh:
    m2=m.copy(); ex=m2.extents
    if ex[2] > max(ex[0], ex[1]) * 1.2:
        m2.apply_transform(tm.transformations.rotation_matrix(np.deg2rad(90), [0,1,0]))
    return m2

def rotZ(m:tm.Trimesh, deg:float)->tm.Trimesh:
    m2=m.copy(); m2.apply_transform(tm.transformations.rotation_matrix(np.deg2rad(deg), [0,0,1])); return m2

def runner_frame(W,D, bar=3.0, z=2.0)->tm.Trimesh:
    segs=[]
    def bar_box(x,y,w,h,t=2.0):
        b=tm.creation.box(extents=[w,h,t]); b.apply_translation([x+w*0.5, y+h*0.5, z+t*0.5]); return b
    segs += [bar_box(0,0,W,bar), bar_box(0,D-bar,W,bar), bar_box(0,0,bar,D), bar_box(W-bar,0,bar,D)]
    return tm.util.concatenate(segs)

def small_tab(x0,y0,x1,y1, w=1.6, t=2.0, z=2.0)->tm.Trimesh:
    L = abs(x1-x0);  L = L if L>=0.1 else 0.1
    b=tm.creation.box(extents=[L, w, t]); b.apply_translation([min(x0,x1)+L*0.5, (y0+y1)*0.5, z+t*0.5]); return b

def _pack(meshes, W, D, margin=6.0, gap=6.0, z0=2.0):
    placed=[]; boxes=[]
    x=y=margin; row_h=0.0
    for m in meshes:
        m2=m.copy()
        minx,miny,minz=m2.bounds[0]
        w,h,_=m2.extents
        if w+2*margin>W or h+2*margin>D:
            raise RuntimeError(f"part too large for plate ({w:.1f}×{h:.1f} > {W}×{D})")
        if x + w + margin > W:
            x=margin; y += row_h + gap; row_h=0.0
        if y + h + margin > D:
            yield placed, boxes
            placed=[]; boxes=[]; x=y=margin; row_h=0.0
        m2.apply_translation([-minx,-miny,-minz]); m2.apply_translation([x,y,z0])
        placed.append(m2); boxes.append((x,y,w,h))
        x += w + gap; row_h=max(row_h, h)
    yield placed, boxes

def _svg_plate(W,D, boxes_with_name, out_path:str, stroke="black"):
    ln=[]
    ln.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}mm" height="{D}mm" viewBox="0 0 {W} {D}">')
    ln.append(f'<rect x="0" y="0" width="{W}" height="{D}" fill="none" stroke="{stroke}" stroke-width="0.2"/>')
    for it in boxes_with_name:
        x,y,w,h = it["x"],it["y"],it["w"],it["h"]
        ln.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" fill="none" stroke="{stroke}" stroke-width="0.2"/>')
        ln.append(f'<text x="{x+1.5:.2f}" y="{y+4:.2f}" font-size="3">{it["name"]}</text>')
        ln.append(f'<text x="{x+1.5:.2f}" y="{y+h-1.5:.2f}" font-size="3">{w:.1f}×{h:.1f}mm</text>')
    ln.append('</svg>')
    with open(out_path,"w",encoding="utf-8") as f: f.write("\n".join(ln))

class PlateParam(BaseModel):
    plate_w: float = 220.0
    plate_d: float = 220.0
    out_dir: str | None = None
    engine_tag: str = "R"     # "R"/"L"
    set: str = "core"         # core / shells / all
    place_shaft_on_last: bool = True
    shaft_angle: float = 45.0
    runner_like: bool = True

def build_plate(p:PlateParam)->dict:
    meta, run_dir, flavor = _load_meta(p.out_dir)
    if not meta: return {"ok":False,"reason":"no_run_found"}
    tag = "_"+p.engine_tag if p.engine_tag else ""
    named_paths = _pick_named(meta, tag, p.set)
    if not named_paths: return {"ok":False,"reason":"no_parts_for_set","set":p.set}

    named_meshes=[(nm, lay_flat(load_mesh(path))) for nm,path in named_paths]
    shafts=[(n,m) for n,m in named_meshes if "shaft_5mm" in n]
    others=[(n,m) for n,m in named_meshes if "shaft_5mm" not in n]

    out_root=os.path.join(run_dir, f"plate_{p.set}_{p.engine_tag or 'X'}_{int(p.plate_w)}x{int(p.plate_d)}")
    os.makedirs(out_root, exist_ok=True)
    out_items=[]; page_idx=0

    for placed, boxes in _pack([m for _,m in others], p.plate_w, p.plate_d, z0=2.0):
        if not placed: continue
        page_idx += 1
        sc=tm.Scene()
        plate = rect_plate(p.plate_w, p.plate_d, 2.0, z=0.0); sc.add_geometry(plate)
        if p.runner_like: sc.add_geometry(runner_frame(p.plate_w, p.plate_d, z=2.0))
        boxes_named=[]
        for (name,_mesh),(m,(x,y,w,h)) in zip(others, zip(placed,boxes)):
            sc.add_geometry(m)
            if p.runner_like:
                tab = small_tab(x-1.0, y+1.6, 3.0, y+1.6, w=1.6, t=2.0, z=2.0)
                sc.add_geometry(tab)
            boxes_named.append({"name":name, "x":float(x), "y":float(y), "w":float(w), "h":float(h)})
        sub = os.path.join(out_root, f"page_{page_idx:02d}"); os.makedirs(sub, exist_ok=True)
        glb = os.path.join(sub,"plate.glb"); sc.export(glb)
        merged = tm.util.concatenate([g for g in sc.geometry.values() if isinstance(g, tm.Trimesh)])
        stl = os.path.join(sub,"plate_merged.stl"); merged.export(stl)
        layout = {"plate_w":p.plate_w,"plate_d":p.plate_d,"parts":boxes_named}
        with open(os.path.join(sub,"layout.json"),"w",encoding="utf-8") as f: json.dump(layout,f,ensure_ascii=False,indent=2)
        _svg_plate(p.plate_w, p.plate_d, boxes_named, os.path.join(sub,"plate.svg"))
        out_items.append({"page":page_idx,"glb":glb,"stl":stl,"dir":sub,"svg":os.path.join(sub,"plate.svg")})

    if shafts and p.place_shaft_on_last:
        page_idx += 1
        sc=tm.Scene()
        plate = rect_plate(p.plate_w, p.plate_d, 2.0, z=0.0); sc.add_geometry(plate)
        if p.runner_like: sc.add_geometry(runner_frame(p.plate_w, p.plate_d, z=2.0))
        boxes_named=[]
        for name,m in shafts:
            m2 = rotZ(lay_flat(m), p.shaft_angle)
            minx,miny,minz = m2.bounds[0]; w,h,_ = m2.extents
            m2.apply_translation([-minx,-miny,-minz])
            x = (p.plate_w - w)/2; y = (p.plate_d - h)/2
            m2.apply_translation([x, y, 2.0])
            sc.add_geometry(m2)
            boxes_named.append({"name":name, "x":float(x), "y":float(y), "w":float(w), "h":float(h)})
        sub = os.path.join(out_root, f"page_{page_idx:02d}"); os.makedirs(sub, exist_ok=True)
        glb = os.path.join(sub,"plate.glb"); sc.export(glb)
        merged = tm.util.concatenate([g for g in sc.geometry.values() if isinstance(g, tm.Trimesh)])
        stl = os.path.join(sub,"plate_merged.stl"); merged.export(stl)
        with open(os.path.join(sub,"layout.json"),"w",encoding="utf-8") as f: json.dump({"plate_w":p.plate_w,"plate_d":p.plate_d,"parts":boxes_named},f,ensure_ascii=False,indent=2)
        _svg_plate(p.plate_w, p.plate_d, boxes_named, os.path.join(sub,"plate.svg"))
        out_items.append({"page":page_idx,"glb":glb,"stl":stl,"dir":sub,"svg":os.path.join(sub,"plate.svg"),"note":"shaft page"})

    info={"ok":True,"plates":out_items,"out_root":out_root,"source_run":run_dir,"flavor":flavor,"count":len(out_items)}
    with open(os.path.join(out_root,"plate_index.json"),"w",encoding="utf-8") as f: json.dump(info,f,ensure_ascii=False,indent=2)
    return info

class StarterParam(BaseModel):
    engine_cc: float = 120.0
    R_casing: float = 30.0
    roller_d: float = 10.0
    roller_w: float = 8.0
def cyl(d,h): return tm.creation.cylinder(radius=d*0.5,height=h,sections=64)
def n20_bracket():
    base=tm.creation.box(extents=[26,14,3]); base.apply_translation([13,7,1.5])
    wallL=tm.creation.box(extents=[26,2.5,12]); wallL.apply_translation([13,1.25,6])
    wallR=tm.creation.box(extents=[26,2.5,12]); wallR.apply_translation([13,12.75,6])
    seat=tm.creation.box(extents=[26,10,2.5]); seat.apply_translation([13,7,10.25])
    return tm.util.concatenate([base,wallL,wallR,seat])
def roller_2mm_shaft(d,w):
    body=cyl(d,w); body.apply_translation([0,0,w*0.5]); return body
def twin_bridge(cc,R):
    w=cc; d=16.0; t=6.0
    beam=tm.creation.box(extents=[w,d,t]); beam.apply_translation([w*0.5,d*0.5,t*0.5])
    pad=tm.creation.box(extents=[18,d,8.0]); L=pad.copy(); L.apply_translation([9,d*0.5,t+4.0])
    Rr=pad.copy(); Rr.apply_translation([w-9,d*0.5,t+4.0]); return tm.util.concatenate([beam,L,Rr])
def build_starter(p:StarterParam)->dict:
    out_dir=os.path.join(RUNS_V23,"starter-"+datetime.datetime.now().strftime("%Y%m%d-%H%M%S")); os.makedirs(out_dir,exist_ok=True)
    parts=[("n20_bracket.stl",n20_bracket()),("roller_2mm_d%.0f_w%.0f.stl"%(p.roller_d,p.roller_w),roller_2mm_shaft(p.roller_d,p.roller_w)),("twin_bridge_cc%.0f.stl"%p.engine_cc,twin_bridge(p.engine_cc,p.R_casing))]
    sc=tm.Scene(); meta=[]
    for n,m in parts:
        path=os.path.join(out_dir,n); m.export(path); meta.append({"name":n,"path":path}); sc.add_geometry(m)
    glb=os.path.join(out_dir,"starter.glb"); sc.export(glb)
    return {"ok":True,"out_dir":out_dir,"glb":glb,"parts":meta}

def _pack_zip(run_dir:str)->str|None:
    if not (run_dir and os.path.isdir(run_dir)): return None
    zip_base=os.path.join(run_dir,"j58_v23_blueprint_pack")
    if os.path.exists(zip_base+".zip"): os.remove(zip_base+".zip")
    shutil.make_archive(zip_base, "zip", run_dir)
    return zip_base+".zip"

class PackParam(BaseModel):
    out_dir: str | None = None
    ensure_plates: bool = True

api=APIRouter(prefix="/wb")
@api.post("/cad/j58_v23_plate")
def j58_v23_plate(p:PlateParam=Body(PlateParam())): return build_plate(p)
@api.post("/cad/j58_v23_starter")
def j58_v23_starter(p:StarterParam=Body(StarterParam())): return build_starter(p)
@api.post("/cad/j58_v23_pack")
def j58_v23_pack(p:PackParam=Body(PackParam())):
    meta, run_dir, flavor = _load_meta(p.out_dir)
    if not meta: return {"ok":False,"reason":"no_run_found"}
    if p.ensure_plates:
        # 기본 R/L core plates 생성 보장
        for tg in ["R","L"]:
            idx_dir=os.path.join(run_dir, f"plate_core_{tg}_220x220")
            if not os.path.exists(idx_dir):
                build_plate(PlateParam(engine_tag=tg, set="core", plate_w=220, plate_d=220, place_shaft_on_last=True, runner_like=True, out_dir=run_dir))
    zp=_pack_zip(run_dir)
    if not zp: return {"ok":False,"reason":"zip_failed"}
    rel=os.path.relpath(zp, start=os.path.abspath("data")).replace("\\","/")
    return {"ok":True,"zip_rel":rel,"run_dir":run_dir}

@api.get("/files/{rel_path:path}")
def send_file(rel_path:str):
    full=_safe(rel_path)
    if not full or not os.path.exists(full): return JSONResponse({"ok":False,"reason":"not_found","rel":rel_path}, status_code=404)
    return FileResponse(full)
