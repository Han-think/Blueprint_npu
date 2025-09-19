import argparse
import statistics as st
import time

import requests

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="http://127.0.0.1")
    parser.add_argument("--ports", nargs="+", type=int, default=[9007])
    args = parser.parse_args()

    for port in args.ports:
        url = f"{args.host}:{port}/moo/health"
        latencies = []
        for _ in range(10):
            start = time.perf_counter()
            response = requests.get(url, timeout=10)
            elapsed = (time.perf_counter() - start) * 1000
            latencies.append(elapsed)
        print(
            {
                "port": port,
                "p50_ms": round(st.median(latencies), 2),
                "p90_ms": round(sorted(latencies)[int(0.9 * len(latencies)) - 1], 2),
                "ok": response.status_code == 200,
            }
        )
