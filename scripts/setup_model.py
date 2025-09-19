import argparse
from pathlib import Path
from typing import Optional

import yaml
from huggingface_hub import snapshot_download


def _first_match(root: Path, pattern: str) -> Optional[str]:
    """Return the first file that matches ``pattern`` under ``root``."""

    matches = list(root.rglob(pattern))
    if matches:
        return str(matches[0])
    fallback = list(root.rglob("*.xml"))
    return str(fallback[0]) if fallback else None


def main(profile: str) -> None:
    with open(profile, "r", encoding="utf-8") as handle:
        cfg = yaml.safe_load(handle)

    repo = cfg.get("hf_repo")
    target = cfg.get("local_dir")
    if not repo or not target:
        raise SystemExit("profile must include hf_repo and local_dir")

    target_path = Path(target)
    target_path.mkdir(parents=True, exist_ok=True)
    print(f"[download] {repo} -> {target_path}")
    snapshot_download(repo_id=repo, local_dir=str(target_path))

    hint = cfg.get("xml_hint", "openvino_model.xml")
    xml = _first_match(target_path, hint)
    print("OV_XML_PATH=", xml if xml else "(not found)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    args = parser.parse_args()
    main(args.profile)
