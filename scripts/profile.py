import os, time, json
from blueprint.pipeline import Pipeline

if __name__ == "__main__":
    pipe = Pipeline(fake=os.getenv("BLUEPRINT_FAKE","0")=="1")
    t0 = time.perf_counter()
    X = pipe.generate(512)
    t1 = time.perf_counter()
    y = pipe.predict(X)
    t2 = time.perf_counter()
    m = pipe.evaluate(X)
    t3 = time.perf_counter()
    res = {
        "device": pipe.device_selected,
        "n": len(X),
        "t_generate_ms": round((t1-t0)*1000,2),
        "t_predict_ms": round((t2-t1)*1000,2),
        "t_evaluate_ms": round((t3-t2)*1000,2)
    }
    print(json.dumps(res, ensure_ascii=False, indent=2))
