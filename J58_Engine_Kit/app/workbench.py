from fastapi import FastAPI
app = FastAPI()

@app.get("/health")
def _h0(): return {"ok": True}

@app.get("/wb/health")
def _h1(): return {"ok": True}

def _add(mod):
    try:
        m = __import__(f"app.{mod}", fromlist=["api"])
        app.include_router(getattr(m, "api"))
    except Exception as e:
        print("warn:", mod, "router not loaded:", e)

for mod in ["j58_v23","j58_plate","j58_blueprint","j58_ai"]:
    _add(mod)
