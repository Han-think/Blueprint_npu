import argparse
import glob
import os
from huggingface_hub import snapshot_download

def main(p: str) -> None:
    import yaml

    cfg = yaml.safe_load(open(p, "r", encoding="utf-8"))
    os.makedirs(cfg["local_dir"], exist_ok=True)
    snapshot_download(repo_id=cfg["hf_repo"], local_dir=cfg["local_dir"])
    cands = glob.glob(
        os.path.join(cfg["local_dir"], "**", cfg.get("xml_hint", "*.xml")),
        recursive=True,
    )
    print("OV_XML_PATH=", cands[0] if cands else "(not found)")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", required=True)
    args = ap.parse_args()
    main(args.profile)
