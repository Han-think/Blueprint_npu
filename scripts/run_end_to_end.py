from __future__ import annotations

import argparse
import base64
import io
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import requests


def _plot_scatter(xs: list[float], ys: list[float], xlabel: str, ylabel: str) -> str:
    fig = plt.figure()
    plt.scatter(xs, ys, s=12)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    buffer = io.BytesIO()
    plt.savefig(buffer, format="png", dpi=120, bbox_inches="tight")
    plt.close(fig)
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()


def main(args: argparse.Namespace) -> None:
    host = args.host.rstrip("/")
    Path("data/reports").mkdir(parents=True, exist_ok=True)

    rocket_resp = requests.post(
        f"{host}:9007/moo/rocket",
        json={"samples": args.rocket_samples, "topk": args.topk, "method": "lhs"},
        timeout=30,
    )
    pencil_resp = requests.post(
        f"{host}:9007/moo/pencil",
        json={
            "samples": args.pencil_samples,
            "topk": args.topk,
            "method": "lhs",
            "M0": 0.9,
            "alt_m": 2000,
        },
        timeout=30,
    )

    rocket_data = rocket_resp.json()
    pencil_data = pencil_resp.json()

    rocket_q = [m["q_bartz_W_m2"] for m in rocket_data.get("top", [])]
    rocket_isp = [m["Isp_s"] for m in rocket_data.get("top", [])]
    rocket_plot = _plot_scatter(rocket_q, rocket_isp, "q_bartz [W/m^2]", "Isp [s]")

    pencil_tsfc = [m["TSFC_kg_per_Ns"] for m in pencil_data.get("top", [])]
    pencil_spec = [m["spec_thrust_N_per_kgps"] for m in pencil_data.get("top", [])]
    pencil_plot = _plot_scatter(pencil_tsfc, pencil_spec, "TSFC [kg/N/s]", "Spec thrust [N/(kg/s)]")

    html = f"""
    <html><head><meta charset='utf-8'><title>Blueprint Report</title></head>
    <body>
    <h2>Rocket Pareto</h2>
    <img src="{rocket_plot}" />
    <h2>Pencil Pareto</h2>
    <img src="{pencil_plot}" />
    <h3>Top Rocket</h3><pre>{json.dumps(rocket_data.get('top', [])[:1], ensure_ascii=False, indent=2)}</pre>
    <h3>Top Pencil</h3><pre>{json.dumps(pencil_data.get('top', [])[:1], ensure_ascii=False, indent=2)}</pre>
    </body></html>
    """

    Path(args.out).write_text(html, encoding="utf-8")
    print(
        json.dumps(
            {
                "report": args.out,
                "rocket": len(rocket_data.get("top", [])),
                "pencil": len(pencil_data.get("top", [])),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="http://127.0.0.1")
    parser.add_argument("--rocket_samples", type=int, default=256)
    parser.add_argument("--pencil_samples", type=int, default=256)
    parser.add_argument("--topk", type=int, default=16)
    parser.add_argument("--out", default="data/reports/report.html")
    main(parser.parse_args())
