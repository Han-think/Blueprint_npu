from fastapi import FastAPI
from importlib import import_module

app = FastAPI()

@app.get("/wb/health")
def _h(): 
    return {"ok": True}

def _try_include(mod: str):
    try:
        m = import_module(f"app.{mod}")
        api = getattr(m, "api")
        app.include_router(api)
        print(f"loaded: {mod}")
    except Exception as e:
        print(f"warn: {mod} router not loaded:", e)

# 필요한 라우터들
for _m in ["j58_v23","j58_plate","j58_blueprint","j58_ai","saturn_s1c","saturn_stack"]:
    _try_include(_m)
