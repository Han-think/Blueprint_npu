from fastapi import FastAPI
from pydantic import BaseModel
import os
from typing import List, Any, Optional
from blueprint.pipeline import Pipeline

app = FastAPI(title="Blueprint Model API")
pipe = Pipeline(
    fake=os.getenv("BLUEPRINT_FAKE","0")=="1",
    device=os.getenv("BLUEPRINT_DEVICE") or None
)

class GenReq(BaseModel):
    count: int = 8

class DesignsReq(BaseModel):
    designs: List[Any]

class OptReq(BaseModel):
    samples: Optional[int] = None
    topk: Optional[int] = None

@app.get("/health")
def health():
    return {"status": "ok", "fake": pipe.fake, "device": pipe.device_selected}

@app.post("/generate")
def generate(req: GenReq):
    return {"designs": pipe.generate(req.count)}

@app.post("/predict")
def predict(req: DesignsReq):
    return {"y": pipe.predict(req.designs)}

@app.post("/evaluate")
def evaluate(req: DesignsReq):
    return {"metrics": pipe.evaluate(req.designs)}

@app.post("/optimize")
def optimize(req: OptReq):
    res = pipe.optimize(samples=req.samples, topk=req.topk)
    return {"top": res}
