"""Download an OpenVINO model snapshot from Hugging Face."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repo",
        default="OpenVINO/Phi-4-mini-instruct-int4-ov",
        help="Hugging Face repository containing OpenVINO assets",
    )
    parser.add_argument(
        "--out",
        default="models/phi4mini_ov",
        help="Directory to place the downloaded snapshot",
    )
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        from huggingface_hub import snapshot_download
    except Exception:  # pragma: no cover - optional dependency hint
        print(
            "huggingface_hub not installed. Please install requirements-ov.txt and retry.",
            file=sys.stderr,
        )
        raise SystemExit(2)

    snapshot_download(
        repo_id=args.repo,
        local_dir=str(out_dir),
        local_dir_use_symlinks=False,
        revision=None,
    )
    print({"ok": True, "dir": str(out_dir)})


if __name__ == "__main__":
    main()
