"""Unified CLI helpers for local development workflows."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional


def _moo_local(
    mode: str,
    samples: int,
    topk: int,
    method: str,
    generations: int,
    *,
    M0: Optional[float] = None,
    alt_m: Optional[float] = None,
) -> Dict[str, Any]:
    if method == "ga":
        raise SystemExit("local GA mode is not supported; use --host to call the API")

    if mode == "rocket":
        from rocket.evaluator import evaluate_batch as evaluate

        if method == "lhs":
            from rocket.sampling import sample_lhs as sampler
        else:
            from rocket.generator import sample as sampler

        designs = sampler(samples)
        metrics = evaluate(designs)
        metrics = [m for m in metrics if m["ok"]]
        metrics.sort(
            key=lambda m: (-m["Isp_s"], m["q_bartz_W_m2"], m["dp_regen_Pa"])
        )
        return {"top": metrics[:topk]}

    from pencil.evaluator import evaluate_batch as evaluate

    if method == "lhs":
        from pencil.sampling import sample_lhs as sampler
    else:
        from pencil.generator import sample as sampler

    designs = sampler(samples, M0_fixed=M0, alt_fixed=alt_m)
    metrics = evaluate(designs)
    metrics = [m for m in metrics if m["ok"]]
    metrics.sort(
        key=lambda m: (-m["spec_thrust_N_per_kgps"], m["TSFC_kg_per_Ns"], m["f_fuel"])
    )
    return {"top": metrics[:topk]}


def _moo_remote(host: str, mode: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    import requests

    url = f"{host.rstrip('/')}/moo/{mode}"
    response = requests.post(url, json=payload, timeout=60)
    response.raise_for_status()
    return response.json()


def _cmd_moo(args: argparse.Namespace) -> None:
    payload = {
        "samples": args.samples,
        "topk": args.topk,
        "method": args.method,
        "generations": args.generations,
        "M0": args.M0,
        "alt_m": args.alt_m,
    }

    if args.host:
        out = _moo_remote(args.host, args.mode, payload)
    else:
        out = _moo_local(
            args.mode,
            args.samples,
            args.topk,
            args.method,
            args.generations,
            M0=args.M0,
            alt_m=args.alt_m,
        )
    print(json.dumps(out, ensure_ascii=False, indent=2))


def _cmd_export_stl(args: argparse.Namespace) -> None:
    data = json.loads(Path(args.pareto).read_text(encoding="utf-8"))
    items = data.get("top", [])
    if not items:
        raise SystemExit("no items in pareto")

    design = items[0].get("design") or {}
    rt_mm = float(design.get("rt_mm", 20.0))
    eps = float(design.get("eps", 20.0))
    spike = float(design.get("spike_deg", 10.0))

    from geometry.export_stl import write_ascii_stl
    from geometry.rocket_geom import nozzle_profile, revolve_to_triangles

    profile = nozzle_profile(rt_mm * 1e-3, eps, spike, n=120)
    tris = revolve_to_triangles(profile, seg=96)
    write_ascii_stl(args.out, "nozzle_top", tris)
    print(
        json.dumps(
            {"out": args.out, "rt_mm": rt_mm, "eps": eps, "spike_deg": spike},
            ensure_ascii=False,
            indent=2,
        )
    )


def _cmd_verify(args: argparse.Namespace) -> None:
    payload = json.loads(Path(args.json).read_text(encoding="utf-8"))

    if args.mode == "rocket":
        from rocket.evaluator import evaluate_batch as evaluate
    else:
        from pencil.evaluator import evaluate_batch as evaluate

    result = evaluate([payload])[0]
    print(json.dumps(result, ensure_ascii=False, indent=2))


def main(argv: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(prog="bp")
    sub = parser.add_subparsers(dest="cmd")

    sp = sub.add_parser("moo", help="run multi-objective optimisation")
    sp.add_argument("--mode", choices=["rocket", "pencil"], required=True)
    sp.add_argument("--samples", type=int, default=256)
    sp.add_argument("--topk", type=int, default=16)
    sp.add_argument("--method", choices=["random", "lhs", "ga"], default="lhs")
    sp.add_argument("--generations", type=int, default=10)
    sp.add_argument("--host", default="", help="remote MOO API base URL")
    sp.add_argument("--M0", type=float, default=None)
    sp.add_argument("--alt_m", type=float, default=None)

    sg = sub.add_parser("export-stl", help="export STL from the top rocket design")
    sg.add_argument("--pareto", required=True)
    sg.add_argument("--out", default="nozzle_top.stl")

    sv = sub.add_parser("verify", help="verify a single design (rocket/pencil)")
    sv.add_argument("--mode", choices=["rocket", "pencil"], required=True)
    sv.add_argument("--json", required=True, help="path to a JSON design file")

    args = parser.parse_args(argv)

    if args.cmd == "moo":
        _cmd_moo(args)
    elif args.cmd == "export-stl":
        _cmd_export_stl(args)
    elif args.cmd == "verify":
        _cmd_verify(args)
    else:
        parser.print_help()
        parser.exit(0)


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    main(sys.argv[1:])

