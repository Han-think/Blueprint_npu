import json
import os
import time

from blueprint.pipeline import Pipeline


if __name__ == "__main__":
    pipeline = Pipeline(fake=os.getenv("BLUEPRINT_FAKE", "0") == "1")
    t0 = time.perf_counter()
    designs = pipeline.generate(512)
    t1 = time.perf_counter()
    predictions = pipeline.predict(designs)
    t2 = time.perf_counter()
    metrics = pipeline.evaluate(designs)
    t3 = time.perf_counter()
    result = {
        "device": pipeline.device_selected,
        "n": len(designs),
        "t_generate_ms": round((t1 - t0) * 1000, 2),
        "t_predict_ms": round((t2 - t1) * 1000, 2),
        "t_evaluate_ms": round((t3 - t2) * 1000, 2),
        "metrics_count": len(metrics),
        "pred_sample": predictions[:2],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
