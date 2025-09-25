from fastapi import FastAPI
app = FastAPI()
@app.get("/wb/health")
def _h(): return {"ok": True}

# auto: j58 v23 router
try:
    from .j58_v23 import api as j58_v23_api
    app.include_router(j58_v23_api)
except Exception as e:
    print('warn: j58 v23 router not loaded:', e)
# auto: j58 plate router
try:
    from .j58_plate import api as j58_plate_api
    app.include_router(j58_plate_api)
except Exception as e:
    print('warn: j58 plate router not loaded:', e)
# auto: j58 blueprint router
try:
    from .j58_blueprint import api as j58_blueprint_api
    app.include_router(j58_blueprint_api)
except Exception as e:
    print('warn: j58 blueprint router not loaded:', e)
