from fastapi import FastAPI
import json, importlib, os

app = FastAPI()

@app.get("/wb/health")
def _h(): return {"ok": True}

@app.get("/wb/models")
def _models():
    reg = _load_registry()
    return {"ok": True, "models": [m.get("id") for m in reg]}

def _load_registry():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    reg_path = os.path.join(root, "ai", "registry.json")
    try:
        with open(reg_path, "r", encoding="utf-8") as f:
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

# 레지스트리대로 라우터 로드
for m in _load_registry():
    for r in m.get("routers", []):
        _include_router(r)
