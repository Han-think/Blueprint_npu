from fastapi import APIRouter
from datetime import datetime
from pathlib import Path

api = APIRouter(prefix="/wb", tags=["saturn"])
ROOT = Path(__file__).resolve().parents[1]
OUT  = ROOT/"data/geometry/cad/saturn_stack"
OUT.mkdir(parents=True, exist_ok=True)

def tank_capsule(x, y, w, h, r, stroke, fill="none", sw=1.3):
    return (
        f"<path d='M {x} {y+r} A {r} {r} 0 0 1 {x+r} {y} L {x+w-r} {y} "
        f"A {r} {r} 0 0 1 {x+w} {y+r} L {x+w} {y+h-r} A {r} {r} 0 0 1 {x+w-r} {y+h} "
        f"L {x+r} {y+h} A {r} {r} 0 0 1 {x} {y+h-r} Z' fill='{fill}' stroke='{stroke}' stroke-width='{sw}'/>"
    )

def label(x, y, txt, color="#fff", fs=12, anchor="start"):
    return f"<text x='{x}' y='{y}' fill='{color}' font-size='{fs}' text-anchor='{anchor}'>{txt}</text>"

def tri_engine(cx, cy, s=18, stroke="#9cd0ff", fill="#1f6aa8"):
    a = s*0.75
    return f"<path d='M {cx-a} {cy} L {cx} {cy+s} L {cx+a} {cy} Z' fill='{fill}' stroke='{stroke}' stroke-width='1.2'/>"

@api.get("/cad/saturn_stack_blueprint")
def saturn_stack_blueprint(scale_mm_per_m: float = 6.0):
    # 근사치(교육용)
    D_33ft = 10.1   # m (S-IC, S-II)
    D_260  = 6.6    # m (S-IVB)
    L_SIC, L_SII, L_SIVB, GAP = 42.1, 24.9, 17.8, 2.0

    mm  = scale_mm_per_m
    pad = 40
    H   = int((L_SIC+L_SII+L_SIVB + GAP*2)*mm + pad*2)
    W   = 820
    x0  = 220

    svg = [f"<svg xmlns='http://www.w3.org/2000/svg' width='{W}' height='{H}' viewBox='0 0 {W} {H}'>",
           "<rect width='100%' height='100%' fill='#0c1e35'/>",
           f"<rect x='8' y='8' width='{W-16}' height='{H-16}' fill='none' stroke='#274a79' stroke-width='2'/>"]

    y = pad
    def stage_box(y, L, D, title, stroke="#fff"):
        xL = x0 - (D*mm)/2; xR = x0 + (D*mm)/2
        svg.append(f"<rect x='{xL}' y='{y}' width='{D*mm}' height='{L*mm}' fill='none' stroke='{stroke}' stroke-width='1.6'/>")
        svg.append(label(xR+10, y+16, title, "#9fd3ff", 12, "start"))
        svg.append(f"<line x1='{x0}' y1='{y}' x2='{x0}' y2='{y+L*mm}' stroke='#6ea3e0' stroke-width='1' stroke-dasharray='6 4'/>")
        return xL, xR

    # S-IC (아래 RP-1 / 가운데 intertank / 위 LOX) + F-1×5
    xL,xR = stage_box(y, L_SIC, D_33ft, "S-IC (33 ft dia)")
    rp1_h, inter_h = L_SIC*0.54, L_SIC*0.05
    lox_h = L_SIC - rp1_h - inter_h
    svg += [
        tank_capsule(xL+6, y+L_SIC*mm-rp1_h*mm, D_33ft*mm-12, rp1_h*mm, 28, "#ffd39f"),
        label(xL-10, y+L_SIC*mm-rp1_h*mm+14, "RP-1 tank", "#ffd39f", 11, "end"),
        f"<rect x='{xL+6}' y='{y+(lox_h*mm)}' width='{D_33ft*mm-12}' height='{inter_h*mm}' fill='none' stroke='#89ffa8' stroke-width='1.2' stroke-dasharray='8 4'/>",
        label(xR+10, y+lox_h*mm+inter_h*mm/2+4, "Intertank", "#89ffa8", 11, "start"),
        tank_capsule(xL+6, y+6, D_33ft*mm-12, lox_h*mm-6, 26, "#9fd3ff"),
        label(xL-10, y+16, "LOX tank", "#9fd3ff", 11, "end"),
    ]
    by = y + L_SIC*mm + 18
    for dx in (-90,-45,0,45,90): svg.append(tri_engine(x0+dx, by))
    svg.append(label(x0, by+28, "F-1 x5", "#9cd0ff", 11, "middle"))
    y += L_SIC*mm + GAP*mm

    # S-II (위 LOX / 공용격벽 / 아래 LH2) + J-2×5
    xL,xR = stage_box(y, L_SII, D_33ft, "S-II (33 ft dia)")
    lox2, lh2_2 = L_SII*0.22, L_SII*0.73
    svg += [
        tank_capsule(xL+6, y+6, D_33ft*mm-12, lox2*mm-6, 24, "#9fd3ff"),
        label(xL-10, y+16, "LOX (common bulkhead)", "#9fd3ff", 11, "end"),
        f"<polygon points='{xL+10},{y+lox2*mm+3} {xR-10},{y+lox2*mm+3} {x0},{y+lox2*mm+21}' fill='none' stroke='#89ffa8' stroke-width='1.2'/>",
        tank_capsule(xL+6, y+lox2*mm+22, D_33ft*mm-12, lh2_2*mm-28, 26, "#b6ffb6"),
        label(xR+10, y+lox2*mm+lh2_2*mm-6, "LH2 tank", "#b6ffb6", 11, "start"),
    ]
    by = y + L_SII*mm + 18
    for dx in (-70,-35,0,35,70): svg.append(tri_engine(x0+dx, by, s=15))
    svg.append(label(x0, by+26, "J-2 x5", "#9cd0ff", 11, "middle"))
    y += L_SII*mm + GAP*mm

    # S-IVB (위 LOX / 공용격벽 / 아래 LH2) + J-2×1
    xL,xR = stage_box(y, L_SIVB, D_260, "S-IVB (21.7 ft dia)")
    lox3, lh2_3 = L_SIVB*0.26, L_SIVB*0.69
    svg += [
        tank_capsule(xL+6, y+6, D_260*mm-12, lox3*mm-6, 18, "#9fd3ff"),
        f"<polygon points='{xL+9},{y+lox3*mm+3} {xR-9},{y+lox3*mm+3} {x0},{y+lox3*mm+17}' fill='none' stroke='#89ffa8' stroke-width='1.2'/>",
        tank_capsule(xL+6, y+lox3*mm+18, D_260*mm-12, lh2_3*mm-24, 20, "#b6ffb6"),
        label(xR+10, y+lox3*mm+lh2_3*mm-6, "LH2 tank", "#b6ffb6", 11, "start"),
        tri_engine(x0, y + L_SIVB*mm + 16, s=16),
        label(x0, y + L_SIVB*mm + 40, "J-2 x1", "#9cd0ff", 11, "middle"),
    ]

    svg += [
        label(28, 26, "SATURN V — Vertical 3-stage blueprint (simplified)", "#fff", 14),
        label(28, 44, f"Scale: {scale_mm_per_m:.1f} mm/m (approx.)", "#9fd3ff", 11),
        f"<rect x='28' y='70' width='170' height='72' fill='none' stroke='#fff' stroke-width='1'/>",
        label(38, 88,  "LOX tank", "#9fd3ff", 11),
        label(38, 104, "LH2 tank", "#b6ffb6", 11),
        label(38, 120, "RP-1 tank", "#ffd39f", 11),
        label(38, 136, "Common bulkhead / Intertank", "#89ffa8", 11),
        "</svg>"
    ]

    out = OUT/f"saturn_stack_{datetime.now():%Y%m%d-%H%M%S}.svg"
    out.write_text("\n".join(svg), encoding="utf-8")
    rel = str(out.relative_to(ROOT)).replace("\\","/")
    return {"ok": True, "svg_rel": rel}
