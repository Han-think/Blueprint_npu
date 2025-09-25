from __future__ import annotations
from fastapi import APIRouter, Body
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import os, json, time, math, random, numpy as np

DATA_DIR = os.path.join("data","ai","j58")
os.makedirs(DATA_DIR, exist_ok=True)
DS_PATH = os.path.join(DATA_DIR,"dataset.jsonl")
MODEL_PATH = os.path.join(DATA_DIR,"model.npz")
LEADER_PATH = os.path.join(DATA_DIR,"leader.json")

RANGES = {
    "L_total": (220.0, 400.0),   # mm
    "R_casing":(22.0,  60.0),    # mm
    "N_fan":   (8,     20),
    "N_comp":  (10,    24),
    "N_turb":  (12,    24),
    "eps":     (8.0,   20.0)
}
FEATS = ["L_total","R_casing","N_fan","N_comp","N_turb","eps","A_in","A_throat","mass_proxy"]

def sample_params(n:int, seed:int|None=None):
    if seed is not None: random.seed(seed)
    out=[]
    for _ in range(n):
        L = RANGES["L_total"][0] + (RANGES["L_total"][1]-RANGES["L_total"][0])*random.random()
        R = RANGES["R_casing"][0]+ (RANGES["R_casing"][1]-RANGES["R_casing"][0])*random.random()
        Nf= int(math.floor(RANGES["N_fan"][0]  + (RANGES["N_fan"][1]  -RANGES["N_fan"][0]  +1)*random.random()))
        Nc= int(math.floor(RANGES["N_comp"][0] + (RANGES["N_comp"][1] -RANGES["N_comp"][0] +1)*random.random()))
        Nt= int(math.floor(RANGES["N_turb"][0] + (RANGES["N_turb"][1] -RANGES["N_turb"][0] +1)*random.random()))
        ep= RANGES["eps"][0]     + (RANGES["eps"][1]    -RANGES["eps"][0]    )*random.random()
        out.append({"L_total":L,"R_casing":R,"N_fan":Nf,"N_comp":Nc,"N_turb":Nt,"eps":ep})
    return out

def features(p:dict)->np.ndarray:
    L,R,Nf,Nc,Nt,ep = p["L_total"],p["R_casing"],p["N_fan"],p["N_comp"],p["N_turb"],p["eps"]
    A_in = math.pi*(0.95*R)**2
    A_th = math.pi*(0.35*R)**2
    mass_proxy = L*(R**2)
    return np.array([L,R,Nf,Nc,Nt,ep, A_in, A_th, mass_proxy], dtype=np.float64)

def score_proxy(p:dict)->float:
    L,R,Nf,Nc,Nt,ep = p["L_total"],p["R_casing"],p["N_fan"],p["N_comp"],p["N_turb"],p["eps"]
    A_in = math.pi*(0.95*R)**2
    thrust = A_in*math.sqrt(max(ep,1.0))*(0.85 + 0.02*Nf + 0.03*Nc + 0.04*Nt)
    penalty = 0.003*(L*(R**2)) + 0.02*(Nf+Nc+Nt) + 0.4*max(0.0, (Nt - Nc*0.9))
    return float(thrust - penalty)

def _load_ds():
    if not os.path.exists(DS_PATH): return [], np.zeros((0,len(FEATS))), np.zeros((0,))
    X=[]; y=[]; rows=[]
    with open(DS_PATH,"r",encoding="utf-8") as f:
        for line in f:
            r=json.loads(line); rows.append(r); X.append(r["x"]); y.append(r["y"])
    return rows, np.asarray(X,dtype=np.float64), np.asarray(y,dtype=np.float64)

def _save_model(obj:dict): np.savez(MODEL_PATH, **obj)
def _load_model():
    if not os.path.exists(MODEL_PATH): return None
    z=np.load(MODEL_PATH, allow_pickle=True); return {k:z[k] for k in z.files}

def _ridge_fit(X, y, l2=1e-3):
    mu = X.mean(axis=0); sig = X.std(axis=0); sig[sig==0]=1.0
    Xs = (X-mu)/sig
    Xb = np.concatenate([Xs, np.ones((Xs.shape[0],1))], axis=1)
    I  = np.eye(Xb.shape[1]); I[-1,-1]=0.0
    w  = np.linalg.pinv(Xb.T@Xb + l2*I) @ (Xb.T@y)
    return w, mu, sig

def _ridge_pred(X, w, mu, sig):
    Xs=(X-mu)/sig; Xb=np.concatenate([Xs, np.ones((Xs.shape[0],1))], axis=1)
    return (Xb@w)

def _update_leader(cand:list[dict]):
    # cand: [{"pred":float, "params":{...}}]
    best = max(cand, key=lambda t:t["pred"]) if cand else None
    if not best: return
    now = {"time":time.time(),"pred":best["pred"],"params":best["params"]}
    try:
        if os.path.exists(LEADER_PATH):
            cur=json.load(open(LEADER_PATH,"r",encoding="utf-8"))
            if cur.get("pred",-1e18) >= now["pred"]: return
    except Exception: pass
    with open(LEADER_PATH,"w",encoding="utf-8") as f: json.dump(now,f,ensure_ascii=False,indent=2)

api = APIRouter(prefix="/wb/ai/j58")

# --------- 1) 데이터 생성 ---------
class GenParam(BaseModel):
    count:int=200
    seed:int|None=None

@api.post("/generate")
def generate(p:GenParam):
    os.makedirs(DATA_DIR, exist_ok=True)
    cnt_before = 0
    if os.path.exists(DS_PATH):
        with open(DS_PATH,"r",encoding="utf-8") as f: cnt_before = sum(1 for _ in f)
    samples = sample_params(p.count, p.seed)
    with open(DS_PATH,"a",encoding="utf-8") as f:
        for s in samples:
            x = features(s).tolist()
            y = score_proxy(s)
            f.write(json.dumps({"x":x,"y":y,"p":s}, ensure_ascii=False) + "\n")
    cnt_after = cnt_before + len(samples)
    return {"ok":True,"dataset":DS_PATH,"added":len(samples),"total":cnt_after}

# --------- 2) 학습(K-fold CV) + 저장 ---------
class TrainCVParam(BaseModel):
    l2_grid:list[float]=[1e-4,3e-4,1e-3,3e-3,1e-2]
    k:int=5
@api.post("/train_cv")
def train_cv(p:TrainCVParam):
    rows, X, y = _load_ds()
    n = X.shape[0]
    if n < max(80, p.k*10):
        return JSONResponse({"ok":False,"reason":"not_enough_data","need_at_least":max(80,p.k*10)}, status_code=400)
    idx = np.arange(n)
    best_alpha=None; best_r2=-1e18
    for alpha in p.l2_grid:
        # K-fold
        np.random.shuffle(idx)
        folds = np.array_split(idx, p.k)
        r2s=[]
        for i in range(p.k):
            te = folds[i]; tr = np.concatenate([folds[j] for j in range(p.k) if j!=i])
            w, mu, sig = _ridge_fit(X[tr], y[tr], alpha)
            yhat = _ridge_pred(X[te], w, mu, sig)
            ssr = ((y[te]-yhat)**2).sum(); sst = ((y[te]-y[te].mean())**2).sum()+1e-9
            r2s.append(1.0-ssr/sst)
        r2m = float(np.mean(r2s))
        if r2m > best_r2: best_r2=r2m; best_alpha=alpha
    # 최종 적합
    w, mu, sig = _ridge_fit(X, y, best_alpha)
    _save_model({"w":w, "mu":mu, "sig":sig, "feats":np.array(FEATS), "time":time.time(), "l2":best_alpha, "n":n, "r2_cv":best_r2})
    return {"ok":True,"model":MODEL_PATH,"best_l2":best_alpha,"r2_cv_mean":best_r2,"n":int(n)}

# --------- 3) 제안(탐색 풀에서 상위 k) + 리더보드 갱신 ---------
class SuggestParam(BaseModel):
    k:int=3
    random_pool:int=1000
    seed:int|None=None
@api.post("/suggest")
def suggest(p:SuggestParam):
    M = _load_model()
    if M is None: return JSONResponse({"ok":False,"reason":"no_model"}, status_code=400)
    if p.seed is not None: random.seed(p.seed)
    cands = sample_params(p.random_pool, p.seed)
    X = np.stack([features(s) for s in cands], axis=0)
    yhat = _ridge_pred(X, M["w"], M["mu"], M["sig"])
    ords = np.argsort(-yhat)[:p.k]
    out=[]
    for i in ords:
        out.append({"rank":len(out)+1,"pred":float(yhat[i]),"params":cands[i]})
    _update_leader(out)
    return {"ok":True,"suggestions":out,"pool":p.random_pool}

# --------- 4) 베스트 반환 / 즉시 빌드 ---------
@api.get("/best")
def best():
    if not os.path.exists(LEADER_PATH): return {"ok":False,"reason":"no_best_yet"}
    return {"ok":True, **json.load(open(LEADER_PATH,"r",encoding="utf-8"))}

class BuildBestParam(BaseModel):
    both_sides: bool = True
@api.post("/best/build")
def build_best(p:BuildBestParam):
    if not os.path.exists(LEADER_PATH): return JSONResponse({"ok":False,"reason":"no_best_yet"}, status_code=400)
    best = json.load(open(LEADER_PATH,"r",encoding="utf-8"))
    try:
        # 로컬 빌더 직접 호출
        from .j58_v23 import build_run, BuildParam
    except Exception as e:
        return JSONResponse({"ok":False,"reason":"builder_not_available","detail":str(e)}, status_code=500)
    bp = BuildParam(**best["params"], both_sides=p.both_sides)
    meta = build_run(bp)
    best["built_at"] = time.time(); best["run"] = meta.get("out_dir")
    with open(LEADER_PATH,"w",encoding="utf-8") as f: json.dump(best,f,ensure_ascii=False,indent=2)
    return {"ok":True,"best":best,"build":meta}

# --------- 5) 상태/UI ---------
@api.get("/status")
def status():
    rows, X, y = _load_ds()
    M=_load_model()
    has_best = os.path.exists(LEADER_PATH)
    return {"ok":True,"dataset_rows":int(X.shape[0]),"has_model":bool(M is not None),"model_path":MODEL_PATH if M is not None else None,"has_best":has_best}

_HTML = """<!doctype html><meta charset='utf-8'>
<title>J58 AI local</title>
<style>body{font:14px/1.4 system-ui;margin:20px;max-width:900px} input{width:90px} button{padding:6px 12px;margin-right:6px}</style>
<h1>J58 AI – Generate · TrainCV · Suggest · BestBuild</h1>
<p><b>Generate</b> count <input id="g_count" type="number" value="200"> seed <input id="g_seed" type="number" value=""><button id="btnGen">Run</button></p>
<p><b>TrainCV</b> l2_grid <input id="t_grid" type="text" value="[0.0001,0.0003,0.001,0.003,0.01]"> k <input id="t_k" type="number" value="5"><button id="btnTrain">Run</button></p>
<p><b>Suggest</b> k <input id="s_k" type="number" value="3"> pool <input id="s_pool" type="number" value="1000"> seed <input id="s_seed" type="number" value=""><button id="btnSuggest">Run</button></p>
<p><b>Best</b> <button id="btnBest">Show</button> <button id="btnBuild">Build</button></p>
<pre id="out" style="background:#111;color:#0f0;padding:12px;white-space:pre-wrap"></pre>
<script>
async function post(u, data){const r=await fetch(u,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)}); const t=await r.text(); if(!r.ok) throw new Error(t); return JSON.parse(t)}
async function get(u){const r=await fetch(u); const t=await r.text(); if(!r.ok) throw new Error(t); return JSON.parse(t)}
function show(x){out.textContent = JSON.stringify(x,null,2)}
btnGen.onclick=async()=>{ try{ show(await post('/wb/ai/j58/generate',{count:+g_count.value, seed:g_seed.value?+g_seed.value:null})) }catch(e){show(e.message)} }
btnTrain.onclick=async()=>{ try{ show(await post('/wb/ai/j58/train_cv',{l2_grid:JSON.parse(t_grid.value), k:+t_k.value})) }catch(e){show(e.message)} }
btnSuggest.onclick=async()=>{ try{ show(await post('/wb/ai/j58/suggest',{k:+s_k.value, random_pool:+s_pool.value, seed:s_seed.value?+s_seed.value:null})) }catch(e){show(e.message)} }
btnBest.onclick=async()=>{ try{ show(await get('/wb/ai/j58/best')) }catch(e){show(e.message)} }
btnBuild.onclick=async()=>{ try{ show(await post('/wb/ai/j58/best/build',{})) }catch(e){show(e.message)} }
</script>"""
@api.get("/ui", response_class=HTMLResponse)
def ui(): return _HTML
