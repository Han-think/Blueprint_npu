from __future__ import annotations

import argparse
import glob
import os
import subprocess
import sys
from typing import List


def _run(cmd: List[str]) -> None:
    print("Running:", " ".join(cmd), flush=True)
    result = subprocess.run(cmd, text=True, capture_output=True)
    print(result.stdout)
    print(result.stderr, file=sys.stderr)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def _find_xml(out: str) -> str | None:
    patterns = ["*.xml", os.path.join("**", "*.xml")]
    for pattern in patterns:
        matches = glob.glob(os.path.join(out, pattern), recursive=True)
        if matches:
            return matches[0]
    return None


def main(ckpt: str, out: str) -> None:
    os.makedirs(out, exist_ok=True)
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
            fallback_cmd = base_cmd.copy()
            idx = fallback_cmd.index("text-generation-with-past")
            fallback_cmd[idx] = "text-generation"
            _run(fallback_cmd)
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
    main(args.ckpt, args.out)
