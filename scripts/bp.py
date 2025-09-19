import argparse
import json
import sys
from pathlib import Path


def moo_local(mode: str, samples: int, topk: int, method: str, generations: int, M0=None, alt=None):
    if mode == "rocket":
        from rocket.evaluator import evaluate_batch as eval_r
        if method == "lhs":
            from rocket.sampling import sample_lhs as sampler
        else:
            from rocket.generator import sample as sampler
        designs = sampler(samples)
        metrics = eval_r(designs)
        metrics = [m for m in metrics if m["ok"]]
        metrics.sort(key=lambda item: (-item["Isp_s"], item["q_bartz_W_m2"], item["dp_regen_Pa"]))
        return {"top": metrics[:topk]}
    else:
        from pencil.evaluator import evaluate_batch as eval_p
        if method == "lhs":
            from pencil.sampling import sample_lhs as sampler
        else:
            from pencil.generator import sample as sampler
        designs = sampler(samples, M0_fixed=M0, alt_fixed=alt)
        metrics = eval_p(designs)
        metrics = [m for m in metrics if m["ok"]]
        metrics.sort(key=lambda item: (-item["spec_thrust_N_per_kgps"], item["TSFC_kg_per_Ns"], item["f_fuel"]))
        return {"top": metrics[:topk]}


def moo_remote(host: str, mode: str, **kwargs):
    import requests

    url = f"{host.rstrip('/')}/moo/{mode}"
    response = requests.post(url, json=kwargs, timeout=60)
    response.raise_for_status()
    return response.json()


def main():
    parser = argparse.ArgumentParser(prog="bp")
    subparsers = parser.add_subparsers(dest="command")

    moo_parser = subparsers.add_parser("moo", help="run multi-objective optimisation")
    moo_parser.add_argument("--mode", choices=["rocket", "pencil"], required=True)
    moo_parser.add_argument("--samples", type=int, default=256)
    moo_parser.add_argument("--topk", type=int, default=16)
    moo_parser.add_argument("--method", choices=["random", "lhs", "ga"], default="lhs")
    moo_parser.add_argument("--generations", type=int, default=10)
    moo_parser.add_argument("--host", default="")
    moo_parser.add_argument("--M0", type=float, default=None)
    moo_parser.add_argument("--alt_m", type=float, default=None)

    export_parser = subparsers.add_parser("export-stl", help="export STL from pareto file")
    export_parser.add_argument("--pareto", required=True)
    export_parser.add_argument("--out", default="nozzle_top.stl")

    verify_parser = subparsers.add_parser("verify", help="verify a single design")
    verify_parser.add_argument("--mode", choices=["rocket", "pencil"], required=True)
    verify_parser.add_argument("--json", required=True)

    args = parser.parse_args()

    if args.command == "moo":
        if args.host:
            result = moo_remote(
                args.host,
                args.mode,
                samples=args.samples,
                topk=args.topk,
                method=args.method,
                generations=args.generations,
                M0=args.M0,
                alt_m=args.alt_m,
            )
        else:
            result = moo_local(
                args.mode,
                args.samples,
                args.topk,
                args.method,
                args.generations,
                M0=args.M0,
                alt=args.alt_m,
            )
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "export-stl":
        from geometry.rocket_geom import nozzle_profile, revolve_to_triangles
        from geometry.export_stl import write_ascii_stl

        data = json.loads(Path(args.pareto).read_text(encoding="utf-8"))
        items = data.get("top", [])
        if not items:
            sys.exit("no items in pareto")
        design = items[0].get("design") or {}
        rt_mm = float(design.get("rt_mm", 20.0))
        eps = float(design.get("eps", 20.0))
        spike = float(design.get("spike_deg", 10.0))
        profile = nozzle_profile(rt_mm * 1e-3, eps, spike, n=120)
        triangles = revolve_to_triangles(profile, seg=96)
        write_ascii_stl(args.out, "nozzle_top", triangles)
        print(json.dumps({"out": args.out, "rt_mm": rt_mm, "eps": eps, "spike_deg": spike}, ensure_ascii=False, indent=2))
    elif args.command == "verify":
        payload = json.loads(Path(args.json).read_text(encoding="utf-8"))
        if args.mode == "rocket":
            from rocket.evaluator import evaluate_batch as eval_r

            result = eval_r([payload])[0]
        else:
            from pencil.evaluator import evaluate_batch as eval_p

            result = eval_p([payload])[0]
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        parser.print_help()
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
