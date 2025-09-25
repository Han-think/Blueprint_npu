from fastapi import FastAPI, APIRouter

app = FastAPI()

# /wb/health
wb = APIRouter(prefix="/wb")
@wb.get("/health")
def _h(): return {"ok": True}
app.include_router(wb)

def _try_include(mod, attr="api"):
    try:
        m = __import__(f"app.{mod}", fromlist=[attr])
        api = getattr(m, attr)
        app.include_router(api)
        print(f"loaded: {mod}")
    except Exception as e:
        print(f"warn: router not loaded: {mod}", e)

# 필요한 라우터들
_try_include("j58_v23")
_try_include("j58_plate")
_try_include("j58_blueprint")
_try_include("j58_ai")
_try_include("saturn_s1c")
_try_include("saturn_stack")
_try_include("saturn_detail")

_try_include("saturn_cad", "api")


_try_include("saturn_overview")
_try_include("saturn_stage_cad")


_try_include("saturn_assembly")


_try_include("j58_engine_cad")


_try_include("glb_tools")


_try_include("glb_pack_named")

