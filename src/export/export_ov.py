from __future__ import annotations

import argparse
import glob
import os
import subprocess
import sys


def _run(cmd):
    print("Running:", " ".join(cmd), flush=True)
    p = subprocess.run(cmd, text=True, capture_output=True)
    print(p.stdout)
    print(p.stderr)
    if p.returncode != 0:
        raise SystemExit(p.returncode)


def _find(out):
    xs = glob.glob(os.path.join(out, "*.xml")) or glob.glob(
        os.path.join(out, "**", "*.xml"), recursive=True
    )
    return xs[0] if xs else None


def main(ckpt: str, out: str):
    os.makedirs(out, exist_ok=True)
    cmd = [
        sys.executable,
        "-m",
        "optimum.exporters.openvino",
        "--model",
        ckpt,
        "--task",
        "text-generation-with-past",
        "--weight-format",
        "fp16",
        "--ov_config",
        "PERFORMANCE_HINT=LATENCY",
        "--output",
        out,
    ]
    try:
        _run(cmd)
        xml = _find(out)
        if not xml:
            cmd[cmd.index("text-generation-with-past")] = "text-generation"
            _run(cmd)
            xml = _find(out)
        if not xml:
            raise RuntimeError("No XML produced")
        print("OK:", xml)
    except SystemExit as e:
        raise e
    except Exception as e:
        print("Export failed:", e)
        raise SystemExit(1)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    main(a.ckpt, a.out)
