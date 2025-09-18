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


def _find(out: str) -> str | None:
    base = Path(out)
    patterns = [base / "*.xml", base / "**" / "*.xml"]
    for pattern in patterns:
        matches = glob.glob(str(pattern), recursive=True)
        if matches:
            return matches[0]
    return None


def main(ckpt: str, out: str) -> None:
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
    except SystemExit:
        raise
    except Exception as exc:  # pragma: no cover - diagnostics
        print("Export failed:", exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ckpt", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    main(args.ckpt, args.out)
