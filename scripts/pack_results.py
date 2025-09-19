"""Bundle generated geometry and Pareto files into a zip archive."""

from __future__ import annotations

import argparse
import zipfile
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out",
        default="exports/blueprint_outputs.zip",
        help="Destination zip archive path",
    )
    args = parser.parse_args()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    base = Path(".")
    geometry_dir = base / "data" / "geometry"
    pareto_dir = base / "data" / "pareto"

    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as zipf:
        if geometry_dir.exists():
            for path in geometry_dir.glob("*.stl"):
                zipf.write(path, arcname=str(path))
        if pareto_dir.exists():
            for path in pareto_dir.glob("*.json"):
                zipf.write(path, arcname=str(path))
        manifest = base / "data" / "manifest.json"
        if manifest.is_file():
            zipf.write(manifest, arcname=str(manifest))
    print({"zip": str(out_path)})


if __name__ == "__main__":
    main()
