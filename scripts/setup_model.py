import argparse
import glob
import os
from pathlib import Path

from huggingface_hub import snapshot_download
import yaml


def _find_xml(root: str, hint: str | None) -> str | None:
    pattern = hint or "*.xml"
    matches = glob.glob(os.path.join(root, "**", pattern), recursive=True)
    if matches:
        return matches[0]
    fallback = glob.glob(os.path.join(root, "**", "*.xml"), recursive=True)
    return fallback[0] if fallback else None


def main(profile: str) -> None:
    cfg = yaml.safe_load(Path(profile).read_text(encoding="utf-8"))
    repo = cfg.get("hf_repo")
    local_dir = cfg.get("local_dir")
    if not repo or not local_dir:
        raise SystemExit("profile must define hf_repo and local_dir")
    Path(local_dir).mkdir(parents=True, exist_ok=True)
    snapshot_download(repo_id=repo, local_dir=local_dir)
    xml = _find_xml(local_dir, cfg.get("xml_hint"))
    print(f"OV_XML_PATH={xml or '(not found)'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    args = parser.parse_args()
    main(args.profile)
