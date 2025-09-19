import argparse
import glob
import os
from typing import Optional

from huggingface_hub import snapshot_download
import yaml


def _first_match(root: str, pattern: str) -> Optional[str]:
    cands = glob.glob(os.path.join(root, "**", pattern), recursive=True)
    if cands:
        return cands[0]
    any_xml = glob.glob(os.path.join(root, "**", "*.xml"), recursive=True)
    return any_xml[0] if any_xml else None


def main(profile: str) -> None:
    cfg = yaml.safe_load(open(profile, "r", encoding="utf-8"))
    repo = cfg.get("hf_repo")
    target = cfg.get("local_dir")
    if not repo or not target:
        raise SystemExit("profile must include hf_repo and local_dir")
    os.makedirs(target, exist_ok=True)
    print(f"[download] {repo} -> {target}")
    snapshot_download(repo_id=repo, local_dir=target)
    hint = cfg.get("xml_hint", "openvino_model.xml")
    xml = _first_match(target, hint)
    print("OV_XML_PATH=", xml if xml else "(not found)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    args = parser.parse_args()
    main(args.profile)
