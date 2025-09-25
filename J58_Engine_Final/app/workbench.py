from __future__ import annotations
import os, io, json, zipfile, math
from pathlib import Path
from typing import Optional, Any, Dict, List
from fastapi import FastAPI, Response
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from pydantic import BaseModel, Field
import numpy as np

try:
    from blueprint.pipeline import Pipeline
except Exception:
    class _Dummy:
        def __init__(self, **kw): self.fake=True; self.device_selected="FAKE"
        def generate(self, n:int): return (np.random.rand(n,3)*2-1).tolist()
        def predict(self, designs): return (1.0 - (np.asarray(designs)**2).sum(1)).tolist()
        def evaluate(self, designs):
            X=np.asarray(designs)
            return [{"ok": bool(np.max(np.abs(x))<=.9 and np.sum(np.abs(x))<=2.0)} for x in X]
        def optimize(self, samples=None, topk=None):
            n=samples or 64; k=topk or 8
            X=self.generate(n); y=self.predict(X); idx=np.argsort(y)[::-1][:k]
            return [{"design":X[i], "score":float(y[i]), "metrics":{}} for i in idx]
    class Pipeline(_Dummy): pass

APP_TITLE = "Blueprint Workbench"
ROOT = Path(".").resolve()
GEOM = ROOT/"data/geometry"; GEOM.mkdir(parents=True, exist_ok=True)
MODELS = ROOT/"models"; MODELS.mkdir(parents=True, exist_ok=True)

app = FastAPI(title=APP_TITLE)


# -- print_slicer routes --
try:
    from app.print_slicer import router as print_router
    app.include_router(print_router)
except Exception as e:
    print('print_slicer disabled:', e)
class SetupReq(BaseModel):
    repo: str = Field(default="OpenVINO/Phi-4-mini-instruct-int4-ov")
    revision: Optional[str] = None

def _download_ov(repo: str, revision: Optional[str])->Dict[str, Any]:
    try:
        from huggingface_hub import hf_hub_download, list_repo_files
        files = list_repo_files(repo_id=repo, revision=revision)
        xml = next((f for f in files if f.lower().endswith(".xml")), None)
        binf= next((f for f in files if f.lower().endswith(".bin")), None)
        if not xml or not binf:
            return {"downloaded": False, "reason": "no xml/bin in repo"}
        xml_path = hf_hub_download(repo_id=repo, filename=xml, revision=revision)
        bin_path = hf_hub_download(repo_id=repo, filename=binf, revision=revision)
        (MODELS/"surrogate.xml").write_bytes(Path(xml_path).read_bytes())
        (MODELS/"surrogate.bin").write_bytes(Path(bin_path).read_bytes())
        return {"downloaded": True, "xml": xml, "bin": binf}
    except Exception as e:
        return {"downloaded": False, "error": str(e)}

@app.post("/wb/setup")
def wb_setup(req: SetupReq):
    res = _download_ov(req.repo, req.revision)
    return {"ok": True, "res": res, "models": [p.name for p in MODELS.glob("*")]}

@app.get("/", response_class=HTMLResponse)
def root():
    return HTMLResponse('<meta http-equiv="refresh" content="0; url=/wb">')

@app.get("/wb", response_class=HTMLResponse)
def wb_page():
    html = f"""
<!doctype html><html><head>
<meta charset="utf-8"/>
<title>{APP_TITLE}</title>
<link rel="stylesheet" href="/wb/static/wb.css"/>
<script defer src="/wb/static/wb.js"></script>
</head><body>
<h1>{APP_TITLE}</h1>
<div class="card">
  <div class="row"><b>Env</b>
    <small>BLUEPRINT_FAKE={os.getenv('BLUEPRINT_FAKE','1')}, BLUEPRINT_DEVICE={os.getenv('BLUEPRINT_DEVICE','')}</small>
  </div>
  <pre id="health" style="margin-top:8px"></pre>
</div>

<div class="card">
  <h2>Step 1. Setup model (OpenVINO IR)</h2>
  <div class="row">
    <label>repo</label><input id="repo" value="OpenVINO/Phi-4-mini-instruct-int4-ov" style="min-width:360px"/>
    <label>rev</label><input id="rev" placeholder="main"/>
    <button class="primary" id="btn-setup">setup</button>
  </div>
  <small>On success, saves models/surrogate.xml and .bin.</small>
</div>

<div class="card">
  <h2>Step 2. Generate nozzle</h2>
  <div class="row">
    <label>mode</label>
    <select id="mode">
      <option value="conical">conical</option>
      <option value="bell">bell</option>
      <option value="aerospike">aerospike</option>
      <option value="pencil">pencil</option>
    </select>
    <label>rt[m]</label><input id="rt" value="0.02"/>
    <label>eps(Ae/At)</label><input id="eps" value="10"/>
    <label>L/rt</label><input id="Lrt" value="6"/>
    <label>nseg</label><input id="nseg" value="96"/>
    <button class="primary" id="btn-gen">generate</button>
  </div>
</div>

<div class="card">
  <h2>Step 3. Optimize (surrogate)</h2>
  <div class="row">
    <label>samples</label><input id="samples" value="{os.getenv('BLUEPRINT_SAMPLES','256')}"/>
    <label>topk</label><input id="topk" value="{os.getenv('BLUEPRINT_TOPK','16')}"/>
    <button class="primary" id="btn-opt">optimize</button>
  </div>
</div>

<div class="card">
  <h2>One-click pipeline</h2>
  <button class="primary" id="btn-runall">run all (setup->generate->opt)</button>
  <button id="btn-refresh">refresh manifest</button>
</div>

<div class="card">
  <h2>Artifacts</h2>
  <ul id="files"></ul>
  <pre id="manifest"></pre>
</div>

<div class="card">
  <h2>Logs</h2>
  <pre id="log"></pre>
</div>
</body></html>
"""
    return HTMLResponse(html)

@app.get("/wb/static/wb.css")
def wb_css(): return FileResponse(str((ROOT/"public/wb.css").resolve()))
@app.get("/wb/static/wb.js")
def wb_js(): return FileResponse(str((ROOT/"public/wb.js").resolve()))

def _new_pipeline()->Pipeline:
    fake = os.getenv("BLUEPRINT_FAKE","1")=="1"
    device = os.getenv("BLUEPRINT_DEVICE") or None
    return Pipeline(fake=fake, device=device)

@app.get("/wb/health")
def wb_health():
    pipe = _new_pipeline()
    return {"status":"ok","fake":getattr(pipe,"fake",True),"device":getattr(pipe,"device_selected","CPU"),
            "models": [p.name for p in MODELS.glob("*")]}

class NozzleReq(BaseModel):
    mode: str = "conical"
    rt: float = 0.02
    eps: float = 10.0
    L_rt: float = 6.0
    nseg: int = 96

def _ring(radius: float, z: float, n: int):
    pts=[]
    for i in range(n):
        a0 = 2*math.pi*i/n
        pts.append((radius*math.cos(a0), radius*math.sin(a0), z))
    return pts

def _tri_strip(a, b):
    tris=[]; n=len(a)
    for i in range(n):
        j=(i+1)%n
        tris.append([a[i], a[j], b[j]])
        tris.append([a[i], b[j], b[i]])
    return tris

def _nozzle_conical(rt, eps, L_rt, nseg):
    re = rt*math.sqrt(eps); L  = L_rt*rt
    return _tri_strip(_ring(rt,0.0,nseg), _ring(re,L,nseg))

def _nozzle_bell(rt, eps, L_rt, nseg):
    re = rt*math.sqrt(eps); L  = L_rt*rt; k=0.382
    tris=[]; steps=24; r_prev, z_prev = rt, 0.0
    for s in range(1, steps+1):
        t = s/steps; z = L*t; r = rt + (re-rt)*(t**(1-k*t))
        a = _ring(r_prev, z_prev, nseg); b = _ring(r, z, nseg)
        tris += _tri_strip(a,b); r_prev, z_prev = r, z
    return tris

def _nozzle_aerospike(rt, eps, L_rt, nseg):
    re = rt*math.sqrt(eps); L  = L_rt*rt; spike_len = L*0.7
    return _tri_strip(_ring(max(rt*0.2, 1e-3), L-spike_len, nseg), _ring(re, L, nseg))

def _nozzle_pencil(rt, eps, L_rt, nseg):
    re = rt*math.sqrt(eps); L  = max(L_rt*rt*0.6, rt*2)
    return _tri_strip(_ring(rt, 0.0, nseg), _ring(re, L, nseg))

def _save_stl(name: str, tris: List[List[List[float]]]):
    out = (ROOT/"data/geometry"/f"{name}.stl")
    with out.open("w", encoding="utf-8") as f:
        f.write("solid "+name+"\n")
        for tri in tris:
            f.write(" facet normal 0 0 0\n  outer loop\n")
            for v in tri:
                f.write(f"   vertex {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
            f.write("  endloop\n endfacet\n")
        f.write("endsolid "+name+"\n")
    return str(out)

@app.post("/wb/nozzle")
def wb_nozzle(req: NozzleReq):
    m = req.mode.lower()
    if m=="conical": tris=_nozzle_conical(req.rt, req.eps, req.L_rt, req.nseg)
    elif m=="bell":  tris=_nozzle_bell(req.rt, req.eps, req.L_rt, req.nseg)
    elif m=="aerospike": tris=_nozzle_aerospike(req.rt, req.eps, req.L_rt, req.nseg)
    elif m=="pencil": tris=_nozzle_pencil(req.rt, req.eps, req.L_rt, req.nseg)
    else: tris=_nozzle_conical(req.rt, req.eps, req.L_rt, req.nseg)
    name = f"nozzle_{m}_rt{req.rt}_eps{req.eps}"
    path = _save_stl(name, tris)
    return {"ok": True, "res": {"saved": Path(path).name, "path": str(Path(path).resolve())}}

class OptReq(BaseModel):
    samples: Optional[int] = None
    topk: Optional[int] = None

@app.post("/wb/optimize")
def wb_optimize(req: OptReq):
    pipe = _new_pipeline()
    res = pipe.optimize(samples=req.samples, topk=req.topk)
    (ROOT/"runs").mkdir(exist_ok=True)
    (ROOT/"runs/last_opt.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "top": res, "device": getattr(pipe, "device_selected", "CPU")}

class RunAllReq(BaseModel):
    repo: str = "OpenVINO/Phi-4-mini-instruct-int4-ov"
    revision: Optional[str] = None
    nozzle: NozzleReq = NozzleReq()
    opt: OptReq = OptReq()

@app.post("/wb/run_all")
def wb_run_all(req: RunAllReq):
    s = wb_setup(SetupReq(repo=req.repo, revision=req.revision))
    n = wb_nozzle(req.nozzle)
    o = wb_optimize(req.opt)
    return {"setup": s, "nozzle": n, "opt": o}

@app.get("/wb/manifest")
def wb_manifest():
    files = [{"name":p.name, "size": p.stat().st_size} for p in (ROOT/"data/geometry").glob("*.stl")]
    return {"count": len(files), "files": files}

@app.get("/wb/files/{name}")
def wb_files(name: str):
    p = (ROOT/"data/geometry"/name).resolve()
    if not p.is_file(): return JSONResponse({"error":"not found"}, status_code=404)
    return FileResponse(str(p))

@app.get("/wb/static/wb.css")
def _css(): return FileResponse(str((ROOT/"public/wb.css").resolve()))
@app.get("/wb/static/wb.js")
def _js():  return FileResponse(str((ROOT/"public/wb.js").resolve()))

@app.get("/wb/export.zip")
def wb_export_zip():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in (ROOT/"data/geometry").glob("*.stl"): zf.write(p, arcname=p.name)
    buf.seek(0)
    return Response(buf.read(), media_type="application/zip",
                    headers={"Content-Disposition":"attachment; filename=geometry.zip"})

from app.cad_pencil import router as pencil2_router
app.include_router(pencil2_router)
# --- auto: include J58 prototype router ---
try:
    from .j58_proto import api as j58_api
    app.include_router(j58_api)
except Exception as e:
    print("warn: j58 router not loaded:", e)
try:
    from .j58_ui import ui as j58_ui
    app.include_router(j58_ui)
except Exception as e:
    print('warn: j58 ui not loaded:', e)



# auto: j58 twin router
try:
    from .j58_twin import api as j58_twin_api
    app.include_router(j58_twin_api)
except Exception as e:
    print('warn: j58 twin router not loaded:', e)

# auto: j58 twin v2 router
try:
    from .j58_twin_v2 import api as j58_twin_v2_api
    app.include_router(j58_twin_v2_api)
except Exception as e:
    print('warn: j58 twin v2 router not loaded:', e)

# auto: j58 v22 router
try:
    from .j58_v22 import api as j58_v22_api
    app.include_router(j58_v22_api)
except Exception as e:
    print('warn: j58_v22 router not loaded:', e)

# auto: j58 v23 router
try:
    from .j58_v23 import api as j58_v23_api
    app.include_router(j58_v23_api)
except Exception as e:
    print('warn: j58_v23 router not loaded:', e)

# auto: j58 plate & starter
try:
    from .j58_plate import api as j58_plate_api
    app.include_router(j58_plate_api)
except Exception as e:
    print('warn: j58 plate router not loaded:', e)

# auto: j58 sprue router
try:
    from .j58_sprue import api as j58_sprue_api
    app.include_router(j58_sprue_api)
except Exception as e:
    print('warn: j58 sprue router not loaded:', e)

# auto: j58 ai/train routers
try:
    from .j58_v23 import api as j58_v23_api
    app.include_router(j58_v23_api)
    from .j58_plate import api as j58_plate_api
    app.include_router(j58_plate_api)
    from .j58_ai import api as j58_ai_api
    app.include_router(j58_ai_api)
    from .j58_ui import ui as j58_ui_router
    app.include_router(j58_ui_router)
except Exception as e:
    print('warn: j58 ai routers not loaded:', e)

# auto: j58 ai router
try:
    from .j58_ai import api as j58_ai_api
    app.include_router(j58_ai_api)
except Exception as e:
    print('warn: j58 ai router not loaded:', e)

# auto: j58 blueprint router
try:
    from .j58_blueprint import api as j58_blueprint_api
    app.include_router(j58_blueprint_api)
except Exception as e:
    print('warn: j58 blueprint not loaded:', e)
