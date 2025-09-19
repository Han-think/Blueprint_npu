from fastapi import FastAPI
from pydantic import BaseModel
import os
from typing import Any, List, Optional

from blueprint.pipeline import Pipeline


app = FastAPI(title="Blueprint Model API")
pipe = Pipeline(
    fake=os.getenv("BLUEPRINT_FAKE", "0") == "1",
    device=os.getenv("BLUEPRINT_DEVICE") or None,
)


class GenReq(BaseModel):
    count: int = 8


class DesignsReq(BaseModel):
    designs: List[Any]


class OptReq(BaseModel):
    samples: Optional[int] = None
    topk: Optional[int] = None


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "fake": pipe.fake, "device": pipe.device_selected}


@app.post("/generate")
def generate(req: GenReq) -> dict[str, Any]:
    return {"designs": pipe.generate(req.count)}


@app.post("/predict")
def predict(req: DesignsReq) -> dict[str, Any]:
    return {"y": pipe.predict(req.designs)}


@app.post("/evaluate")
def evaluate(req: DesignsReq) -> dict[str, Any]:
    return {"metrics": pipe.evaluate(req.designs)}


@app.post("/optimize")
def optimize(req: OptReq) -> dict[str, Any]:
    res = pipe.optimize(samples=req.samples, topk=req.topk)
    return {"top": res}
