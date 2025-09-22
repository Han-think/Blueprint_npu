# 사용: python scripts/bench_surrogate.py --n 2048
import argparse, time, json, numpy as np
from pathlib import Path

from blueprint.pipeline import Pipeline

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=1024)
    a=ap.parse_args()
    pipe = Pipeline(fake=True)  # 실제 IR 쓰려면 .env에서 BLUEPRINT_FAKE=0
    X = pipe.generate(a.n)
    t0=time.perf_counter(); y=pipe.predict(X); t1=time.perf_counter()
    res={"n":a.n,"device":pipe.device_selected,
         "t_predict_ms":round((t1-t0)*1000,2),
         "mem_hint":"python only"}
    Path("data/bench").mkdir(parents=True, exist_ok=True)
    Path("data/bench/bench.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False))
