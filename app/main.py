from fastapi import FastAPI
from pydantic import BaseModel
import os

 codex/initialize-npu-inference-template-v1n7c2
from typing import Any, List, Optional


from typing import List, Any, Optional
 main
from blueprint.pipeline import Pipeline

app = FastAPI(title="Blueprint Model API")
pipe = Pipeline(
 codex/initialize-npu-inference-template-v1n7c2
    fake=os.getenv("BLUEPRINT_FAKE", "0") == "1",
    device=os.getenv("BLUEPRINT_DEVICE") or None,
)


class GenReq(BaseModel):
    count: int = 8


class DesignsReq(BaseModel):
    designs: List[Any]



    fake=os.getenv("BLUEPRINT_FAKE","0")=="1",
    device=os.getenv("BLUEPRINT_DEVICE") or None
)

class GenReq(BaseModel):
    count: int = 8

class DesignsReq(BaseModel):
    designs: List[Any]

 main
class OptReq(BaseModel):
    samples: Optional[int] = None
    topk: Optional[int] = None

 codex/initialize-npu-inference-template-v1n7c2


 main
@app.get("/health")
def health():
    return {"status": "ok", "fake": pipe.fake, "device": pipe.device_selected}

 codex/initialize-npu-inference-template-v1n7c2


 main
@app.post("/generate")
def generate(req: GenReq):
    return {"designs": pipe.generate(req.count)}

 codex/initialize-npu-inference-template-v1n7c2


 main
@app.post("/predict")
def predict(req: DesignsReq):
    return {"y": pipe.predict(req.designs)}

 codex/initialize-npu-inference-template-v1n7c2


 main
@app.post("/evaluate")
def evaluate(req: DesignsReq):
    return {"metrics": pipe.evaluate(req.designs)}

 codex/initialize-npu-inference-template-v1n7c2


 main
@app.post("/optimize")
def optimize(req: OptReq):
    res = pipe.optimize(samples=req.samples, topk=req.topk)
    return {"top": res}
