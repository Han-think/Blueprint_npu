from __future__ import annotations

import argparse
import glob
import os
import subprocess
import sys
from pathlib import Path


def _run(cmd: list[str]) -> None:
    print("Running:", " ".join(cmd), flush=True)
    proc = subprocess.run(cmd, text=True, capture_output=True)
    print(proc.stdout)
    print(proc.stderr)
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)


def _find_xml(out_dir: str) -> str | None:
    matches = glob.glob(os.path.join(out_dir, "*.xml"))
    if matches:
        return matches[0]
    return next(iter(glob.glob(os.path.join(out_dir, "**", "*.xml"), recursive=True)), None)


def export_model(ckpt: str, out: str) -> None:
    Path(out).mkdir(parents=True, exist_ok=True)
    base_cmd = [
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
        _run(base_cmd)
        xml = _find_xml(out)
        if not xml:
            fallback = base_cmd.copy()
            idx = fallback.index("text-generation-with-past")
            fallback[idx] = "text-generation"
            _run(fallback)
            xml = _find_xml(out)
        if not xml:
            raise RuntimeError("No XML produced")
        print("OK:", xml)
    except SystemExit:
        raise
    except Exception as exc:
        print("Export failed:", exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ckpt", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    export_model(args.ckpt, args.out)
