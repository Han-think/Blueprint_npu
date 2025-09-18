from __future__ import annotations

import json
import os
import time

from blueprint.pipeline import Pipeline


def main() -> None:
    pipe = Pipeline(
        fake=os.getenv("BLUEPRINT_FAKE", "0") == "1",
        device=os.getenv("BLUEPRINT_DEVICE") or None,
    )
    t0 = time.perf_counter()
    x = pipe.generate(512)
    t1 = time.perf_counter()
    y = pipe.predict(x)
    t2 = time.perf_counter()
    metrics = pipe.evaluate(x)
    t3 = time.perf_counter()
    res = {
        "device": pipe.device_selected,
        "n": len(x),
        "t_generate_ms": round((t1 - t0) * 1000, 2),
        "t_predict_ms": round((t2 - t1) * 1000, 2),
        "t_evaluate_ms": round((t3 - t2) * 1000, 2),
        "metrics_ok": sum(1 for m in metrics if m["ok"]),
    }
    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
