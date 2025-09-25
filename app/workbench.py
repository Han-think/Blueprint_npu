from fastapi import FastAPI
import json, importlib, os
app = FastAPI()

@app.get("/wb/health")
def _h(): return {"ok": True}

@app.get("/wb/models")
def _models():
    reg = _load_registry()
    return {"ok": True, "models": [m.get("id") for m in reg]}

@app.get("/wb/debug_routes")
def _routes():
    return {"routes":[(r.path, ",".join(r.methods)) for r in app.router.routes]}

def _load_registry():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    reg_path = os.path.join(root, "ai", "registry.json")
    try:
        with open(reg_path, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception as e:
        print("warn: registry load failed:", e)
        return []

def _include_router(mod_name: str):
    try:
        m = importlib.import_module(f"app.{mod_name}")
        api = getattr(m, "api")
        app.include_router(api)
        print("loaded:", mod_name)
    except Exception as e:
        print("warn: router not loaded:", mod_name, e)

routers=[]
for m in _load_registry():
    routers += m.get("routers", [])
if not routers:
    routers = ["j58_v23","j58_plate","j58_blueprint","j58_ai"]
for r in routers: _include_router(r)

_try_include("saturn_stack", "api")

