
import argparse
import glob
import os
from huggingface_hub import snapshot_download


    cands = glob.glob(
        os.path.join(cfg["local_dir"], "**", cfg.get("xml_hint", "*.xml")),
        recursive=True,
    )
    print("OV_XML_PATH=", cands[0] if cands else "(not found)")

