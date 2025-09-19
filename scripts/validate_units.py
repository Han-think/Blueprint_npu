import json
import statistics as stats
import sys
from pathlib import Path

codex/initialize-npu-inference-template-ys4nnv

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rocket.generator import sample as rocket_sample_rand
from rocket.sampling import sample_lhs as rocket_sample_lhs
from pencil.generator import sample as pencil_sample_rand
from pencil.sampling import sample_lhs as pencil_sample_lhs

main

def _summary(rows, keys):
    summary = {}
    for key in keys:
        values = [float(row[key]) for row in rows]
        summary[key] = {
            "min": min(values),
            "max": max(values),
            "mean": stats.mean(values),
        }
    return summary


codex/initialize-npu-inference-template-ys4nnv
def main() -> None:
    ROOT = Path(__file__).resolve().parent.parent
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from rocket.generator import sample as rocket_sample_rand
    from rocket.sampling import sample_lhs as rocket_sample_lhs
    from pencil.generator import sample as pencil_sample_rand
    from pencil.sampling import sample_lhs as pencil_sample_lhs


if __name__ == "__main__":
main
    units = json.loads(Path("data/schema_units.json").read_text(encoding="utf-8"))
    rocket_rand = rocket_sample_rand(100)
    rocket_lhs = rocket_sample_lhs(100, seed=42)
    pencil_rand = pencil_sample_rand(100, seed=0)
    pencil_lhs = pencil_sample_lhs(100, seed=42)

    report = {
        "units_version": units["version"],
        "rocket_random": _summary(rocket_rand, units["rocket"].keys()),
        "rocket_lhs": _summary(rocket_lhs, units["rocket"].keys()),
        "pencil_random": _summary(pencil_rand, units["pencil"].keys()),
        "pencil_lhs": _summary(pencil_lhs, units["pencil"].keys()),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
codex/initialize-npu-inference-template-ys4nnv


if __name__ == "__main__":
    main()

main
