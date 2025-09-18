from __future__ import annotations

import argparse
import glob
import os
from pathlib import Path

from huggingface_hub import snapshot_download
import yaml


def _pick(root: str, hint: str) -> str | None:
    cands = glob.glob(str(Path(root) / "**" / hint), recursive=True)
    if cands:
        return cands[0]
    any_xml = glob.glob(str(Path(root) / "**" / "*.xml"), recursive=True)
    return any_xml[0] if any_xml else None


def main(profile: str) -> None:
    with open(profile, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    for key in ("gen", "sim"):
        sec = cfg.get(key, {}) or {}
        repo = sec.get("hf_repo")
        local = sec.get("local_dir")
        if not repo or not local:
            print(f"[{key}] skip (no repo/local_dir)")
            continue
        os.makedirs(local, exist_ok=True)
        print(f"[{key}] download {repo} -> {local}")
        snapshot_download(repo_id=repo, local_dir=local)
        xml = _pick(local, sec.get("xml_hint", "openvino_model.xml"))
        print(f"[{key}] OV xml = {xml}")

    print("Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    args = parser.parse_args()
    main(args.profile)
